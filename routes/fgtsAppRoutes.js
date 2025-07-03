const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const upload = require('../middlewares/upload');

const UPLOAD_FOLDER = 'uploads';
if (!fs.existsSync(UPLOAD_FOLDER)) { fs.mkdirSync(UPLOAD_FOLDER); }

router.get('/', (req, res) => { res.render('fgts-app/fgts-index'); });

router.post('/', upload.array('txt_files', 2), async (req, res) => 
{
    if (!req.files || req.files.length !== 2) 
    {
        req.flash('error', 'Por favor, envie exatamente dois arquivos para comparação.');
        return res.redirect('/fgts');
    }

    try 
    {
        const files = req.files;
        const filepaths = files.map(file => file.path);
        
        const pythonPath = path.resolve(__dirname, '..', 'venv', 'Scripts', 'python.exe');
        const scriptPath = path.resolve(__dirname, '..', 'fgts-app.py');

        const python = spawn(pythonPath, [scriptPath, ...filepaths]);
        
        let resultData = Buffer.from('');
        let errorData = Buffer.from('');
        
        python.stdout.on('data', (data) => { resultData = Buffer.concat([resultData, data]); });
        
        python.stderr.on('data', (data) => 
        {
            errorData = Buffer.concat([errorData, data]);
            console.error(`[PYTHON ERROR] ${data}`);
        });
        
        python.on('close', (code) => 
        {
            files.forEach(file => 
            {
                try { fs.unlinkSync(file.path); } 
                catch (err) { console.error(err); }
            });

            if (code !== 0) 
            {
                req.flash('error', `Erro no processamento: ${errorData.toString()}`);
                return res.redirect('/fgts');
            }
            
            res.set({ 'Content-Type': 'application/zip', 'Content-Disposition': 'attachment; filename=resultados_fgts.zip' });
            res.send(resultData);
        });
        
    } 
    catch (err) 
    {
        console.error(err);
        req.flash('error', 'Erro ao processar os arquivos.');
        return res.redirect('/fgts');
    }
});

module.exports = router;