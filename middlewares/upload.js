const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const unidecode = require('unidecode');

const UPLOAD_FOLDER = 'uploads';
if (!fs.existsSync(UPLOAD_FOLDER)) fs.mkdirSync(UPLOAD_FOLDER);

const storage = multer.diskStorage({
  destination: function (req, file, cb) { cb(null, 'uploads/'); },
  filename: (req, file, cb) => 
  {
    const ext = path.extname(file.originalname) || '.pdf';
    let base = path.basename(file.originalname, ext);

    try { base = Buffer.from(base, 'latin1').toString('utf8'); } 
    catch (e) { console.warn('Não foi possível converter codificação:', e); }

    let nomeLimpo = unidecode(base);
    nomeLimpo = nomeLimpo.replace(/[^\w.\-]+/g, '_');

    const finalName = `${uuidv4()}_${nomeLimpo}${ext}`;
    cb(null, finalName);
  }
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 100 * 1024 * 1024 } // Limite de 100MB
});

module.exports = upload;