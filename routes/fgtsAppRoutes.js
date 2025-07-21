const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const upload = require('../middlewares/upload');
const os = require('os');

const UPLOAD_FOLDER = 'uploads';
if (!fs.existsSync(UPLOAD_FOLDER)) { fs.mkdirSync(UPLOAD_FOLDER); }

router.get('/', (req, res) => { res.render('fgts-app/fgts-index'); });

router.post('/', upload.array('txt_files', 2), async (req, res) => 
{
    if (!req.files) 
    {
        req.flash('error', 'Por favor, envie exatamente dois arquivos para comparação.');
        return res.redirect('/fgts');
    }

    try 
    {
        const files = req.files;
        const filepaths = files.map(f => f.path);

        const isWindows = os.platform() === 'win32';
        const pythonPath = path.resolve(__dirname, '..', 'venv', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python');
        const scriptPath = path.resolve(__dirname, '..', 'fgts-app.py');

        const python = spawn(pythonPath, [scriptPath, ...filepaths]);

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => { stdout += data.toString(); });
        python.stderr.on('data', (data) => { stderr += data.toString(); });

        python.on('close', (code) => 
        {
            files.forEach(f => { try { fs.unlinkSync(f.path); } catch (err) { console.error(err); } });

            if (code !== 0) 
            {
                console.error(`[PYTHON ERROR]: ${stderr}`);
                req.flash('error', `Erro no processamento: ${stderr}`);
                return res.redirect('/fgts');
            }

            const zipPath = stdout.trim();

            if (!fs.existsSync(zipPath)) 
            {
                req.flash('error', 'Arquivo não encontrado após processamento.');
                return res.redirect('/fgts');
            }

            res.download(zipPath, 'resultados_fgts.zip', (err) => 
            {
                try { fs.unlinkSync(zipPath); } catch (e) { console.error(e); }

                if (err) 
                {
                    console.error(err);
                    req.flash('error', 'Erro ao baixar o arquivo.');
                    return res.redirect('/fgts');
                }
            });
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