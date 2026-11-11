/**
 * 上傳前讀取 xlsx 各工作表的行數，不依賴第三方庫。
 *
 * xlsx 是 zip 壓縮包；每個工作表 XML 開頭通常有 <dimension ref="A1:N33064"/> 記錄使用範圍。
 * 這裡只解壓 workbook.xml、關係表和每個工作表開頭的一小段，不解析單元格內容。
 * 解壓用瀏覽器自帶的 DecompressionStream('deflate-raw')。
 *
 * readXlsxSheetRows(file) 返回：
 *   [{ name, rows }, ...]  讀取成功
 *   null                   無法預先讀取（如缺少 dimension），交給伺服器檢查
 * 文件不是有效的 xlsx（不是 zip）時拋出錯誤。
 */
(function () {
    const SIG_EOCD = 0x06054b50;          // zip 結尾記錄
    const SIG_CENTRAL = 0x02014b50;       // 中央目錄項
    const SIG_LOCAL = 0x04034b50;         // 本地文件頭
    const SHEET_HEAD_BYTES = 4096;        // 工作表 XML 只讀開頭這麼多字節
    const XML_ENTITIES = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'" };

    class NotXlsxError extends Error {}

    /** 讀取 zip 中央目錄，返回 { 路徑: { method, compressedSize, localOffset } } */
    function readCentralDirectory(bytes) {
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        const minStart = Math.max(0, bytes.length - 22 - 0xffff);
        let eocd = -1;
        for (let i = bytes.length - 22; i >= minStart; i--) {
            if (view.getUint32(i, true) === SIG_EOCD) {
                eocd = i;
                break;
            }
        }
        if (eocd < 0) {
            throw new NotXlsxError('不是有效的 xlsx 文件');
        }

        const count = view.getUint16(eocd + 10, true);
        let pos = view.getUint32(eocd + 16, true);
        if (count === 0xffff || pos === 0xffffffff) {
            return null;  // zip64，本工具的文件不會這麼大，交給伺服器
        }

        const decoder = new TextDecoder('utf-8');
        const entries = {};
        for (let i = 0; i < count; i++) {
            if (pos + 46 > bytes.length || view.getUint32(pos, true) !== SIG_CENTRAL) {
                throw new NotXlsxError('不是有效的 xlsx 文件');
            }
            const nameLen = view.getUint16(pos + 28, true);
            const extraLen = view.getUint16(pos + 30, true);
            const commentLen = view.getUint16(pos + 32, true);
            const name = decoder.decode(bytes.subarray(pos + 46, pos + 46 + nameLen));
            entries[name] = {
                method: view.getUint16(pos + 10, true),
                compressedSize: view.getUint32(pos + 20, true),
                localOffset: view.getUint32(pos + 42, true),
            };
            pos += 46 + nameLen + extraLen + commentLen;
        }
        return entries;
    }

    /** 從 deflate 數據流解壓，最多取 maxBytes 字節後停止 */
    async function inflate(data, maxBytes) {
        const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
        const reader = stream.getReader();
        const chunks = [];
        let total = 0;
        try {
            while (!maxBytes || total < maxBytes) {
                const { done, value } = await reader.read();
                if (done) {
                    break;
                }
                chunks.push(value);
                total += value.length;
            }
        } finally {
            reader.cancel().catch(() => {});
        }
        const out = new Uint8Array(total);
        let offset = 0;
        for (const chunk of chunks) {
            out.set(chunk, offset);
            offset += chunk.length;
        }
        return maxBytes ? out.subarray(0, maxBytes) : out;
    }

    /** 讀取壓縮包內某個文件的文字；maxBytes 為空時讀全部 */
    async function readEntryText(bytes, entries, path, maxBytes) {
        const entry = entries[path];
        if (!entry) {
            return null;
        }
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        const local = entry.localOffset;
        if (local + 30 > bytes.length || view.getUint32(local, true) !== SIG_LOCAL) {
            return null;
        }
        const start = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
        const data = bytes.subarray(start, start + entry.compressedSize);

        let raw;
        if (entry.method === 0) {
            raw = maxBytes ? data.subarray(0, maxBytes) : data;
        } else if (entry.method === 8) {
            raw = await inflate(data, maxBytes);
        } else {
            return null;
        }
        return new TextDecoder('utf-8').decode(raw);
    }

    function xmlAttr(tag, namePattern) {
        const match = new RegExp(`\\s${namePattern}="([^"]*)"`).exec(tag);
        return match ? match[1].replace(/&(amp|lt|gt|quot|apos);/g, m => XML_ENTITIES[m]) : null;
    }

    /** 關係表裡的 Target 轉成壓縮包內路徑（相對於 xl/ 目錄，或以 / 開頭的絕對路徑） */
    function resolveTarget(target) {
        return target.startsWith('/') ? target.slice(1) : 'xl/' + target.replace(/^\.\//, '');
    }

    /** "A1:N33064" → 33064；"A1" → 1 */
    function lastRowOf(ref) {
        const end = ref.split(':').pop();
        const match = /(\d+)$/.exec(end);
        return match ? parseInt(match[1], 10) : null;
    }

    async function readXlsxSheetRows(file) {
        const bytes = new Uint8Array(await file.arrayBuffer());
        const entries = readCentralDirectory(bytes);
        if (!entries) {
            return null;
        }

        const workbookXml = await readEntryText(bytes, entries, 'xl/workbook.xml');
        const relsXml = await readEntryText(bytes, entries, 'xl/_rels/workbook.xml.rels');
        if (!workbookXml || !relsXml) {
            return null;
        }

        const targets = {};
        for (const tag of relsXml.match(/<Relationship\b[^>]*>/g) || []) {
            targets[xmlAttr(tag, 'Id')] = xmlAttr(tag, 'Target');
        }

        const sheets = [];
        for (const tag of workbookXml.match(/<sheet\b[^>]*>/g) || []) {
            const name = xmlAttr(tag, 'name');
            const target = targets[xmlAttr(tag, '[\\w]+:id')];
            if (name === null || !target) {
                return null;
            }
            const head = await readEntryText(bytes, entries, resolveTarget(target), SHEET_HEAD_BYTES);
            const dim = head && /<dimension ref="([^"]+)"/.exec(head);
            const rows = dim && lastRowOf(dim[1]);
            if (!rows) {
                return null;
            }
            sheets.push({ name, rows });
        }
        return sheets.length > 0 ? sheets : null;
    }

    window.readXlsxSheetRows = readXlsxSheetRows;
    window.NotXlsxError = NotXlsxError;
})();
