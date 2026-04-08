const zlib = require('zlib');
const fs = require('fs');

function makePng32(r, g, b) {
  const w = 32, h = 32;
  const raw = Buffer.alloc(h * (1 + w * 4));
  for (let y = 0; y < h; y++) {
    const base = y * (1 + w * 4);
    raw[base] = 0;
    for (let x = 0; x < w; x++) {
      const p = base + 1 + x * 4;
      let pr = 0, pg = 0, pb = 0, pa = 0;
      // Cuerpo
      if (x >= 4 && x <= 27 && y >= 8 && y <= 25) { pr=r; pg=g; pb=b; pa=255; }
      // Franja superior oscura
      if (x >= 4 && x <= 27 && y >= 8 && y <= 10)  { pr=Math.floor(r*0.45); pg=Math.floor(g*0.45); pb=Math.floor(b*0.45); pa=255; }
      // Ranura
      if (x >= 8 && x <= 23 && y >= 14 && y <= 15)  { pr=Math.floor(r*0.45); pg=Math.floor(g*0.45); pb=Math.floor(b*0.45); pa=255; }
      // Tirador
      if (x >= 13 && x <= 18 && y >= 20 && y <= 22) { pr=200; pg=160; pb=80; pa=255; }
      // Borde inferior
      if (x >= 4 && x <= 27 && y >= 24 && y <= 25)  { pr=Math.floor(r*0.45); pg=Math.floor(g*0.45); pb=Math.floor(b*0.45); pa=255; }
      raw[p]=pr; raw[p+1]=pg; raw[p+2]=pb; raw[p+3]=pa;
    }
  }
  const idat = zlib.deflateSync(raw);

  function crc32(buf) {
    let c = 0xFFFFFFFF;
    const t = Array.from({length:256}, (_,i) => {
      let n = i;
      for (let j = 0; j < 8; j++) n = (n & 1) ? (0xEDB88320 ^ (n >>> 1)) : (n >>> 1);
      return n;
    });
    for (const byte of buf) c = t[(c ^ byte) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  function chunk(type, data) {
    const t = Buffer.from(type, 'ascii');
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const payload = Buffer.concat([t, data]);
    const crcBuf = Buffer.alloc(4); crcBuf.writeUInt32BE(crc32(payload));
    return Buffer.concat([len, payload, crcBuf]);
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8]=8; ihdr[9]=6; ihdr[10]=0; ihdr[11]=0; ihdr[12]=0;

  const sig = Buffer.from([137,80,78,71,13,10,26,10]);
  return Buffer.concat([sig, chunk('IHDR',ihdr), chunk('IDAT',idat), chunk('IEND',Buffer.alloc(0))]);
}

function makeIco(pngBuf) {
  const buf = Buffer.alloc(6 + 16 + pngBuf.length);
  buf.writeUInt16LE(0, 0);
  buf.writeUInt16LE(1, 2);
  buf.writeUInt16LE(1, 4);
  buf[6]=32; buf[7]=32; buf[8]=0; buf[9]=0;
  buf.writeUInt16LE(1, 10);
  buf.writeUInt16LE(32, 12);
  buf.writeUInt32LE(pngBuf.length, 14);
  buf.writeUInt32LE(22, 18);
  pngBuf.copy(buf, 22);
  return buf;
}

fs.writeFileSync('icon-green.ico', makeIco(makePng32(34, 197, 94)));
fs.writeFileSync('icon-red.ico',   makeIco(makePng32(239, 68, 68)));
console.log('Iconos generados OK');
