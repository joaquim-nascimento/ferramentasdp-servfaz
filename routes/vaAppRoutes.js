const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const upload = require('../middlewares/upload');
const os = require('os');

const UPLOAD_FOLDER = 'uploads';
if ( !fs.existsSync(UPLOAD_FOLDER)) { fs.mkdirSync(UPLOAD_FOLDER); }

router.get('/', (req, res) => { res.render('va-app/index'); });

router.post('/', upload.fields([ { name: 'planilha', maxCount: 1 }, { name: 'template', maxCount: 1 } ]), async (req, res) => 
{
    if (!req.files || !req.files.planilha || !req.files.template) 
    {
        req.flash('error', 'Envie a planilha e o template.');
        return res.redirect('/va');
    }

    try {
        const planilhaPath = req.files.planilha[0].path;
        const templatePath = req.files.template[0].path;

        const isWindows = os.platform() === 'win32';
        const pythonPath = path.resolve(__dirname, '..', 'venv', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python');
        const scriptPath = path.resolve(__dirname, '..', 'va-app.py');

        const python = spawn(pythonPath, [scriptPath, planilhaPath, templatePath]);

        let outputPath = '';
        let stdErr = Buffer.from('');

        python.stdout.on('data', (data) => { outputPath += data.toString(); });
        python.stderr.on('data', (data) => { stdErr = Buffer.concat([stdErr, data]); });

        python.on('close', (code) => 
        {
            fs.unlinkSync(planilhaPath);
            fs.unlinkSync(templatePath);

            if (code !== 0 || !fs.existsSync(outputPath.trim())) 
            {
                req.flash('error', `Erro ao gerar arquivo: ${stdErr.toString()}`);
                return res.redirect('/va');
            }

            res.download(outputPath.trim(), 'va.txt', (err) => 
            {
                if (err) console.error(err);
                fs.unlinkSync(outputPath.trim());
            });
        });

    } 
    catch (err) 
    {
        console.error(err);
        req.flash('error', 'Erro no servidor.');
        res.redirect('/va');
    }
});

module.exports = router;