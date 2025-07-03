const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const upload = require('../middlewares/upload');

const UPLOAD_FOLDER = 'uploads';
if (!fs.existsSync(UPLOAD_FOLDER)) { fs.mkdirSync(UPLOAD_FOLDER); }

router.get('/', (req, res) => { res.render('ponto-app/ponto-index', { messages: req.flash() }); });
router.get('/aguarde', (req, res) => { res.render('ponto-app/aguarde', { messages: req.flash() }); });

router.post('/', upload.single('pdf_file'), async (req, res) => 
{
    if (!req.file) 
    {
        console.error('Nenhum arquivo selecionado.');
        req.flash('error', 'Nenhum arquivo selecionado.');
        return res.redirect('/ponto');
    }

    try 
    {
        const taskId = uuidv4();
        const file = req.file;
        const filename = `${taskId}_${file.originalname}`;
        const filepath = path.join(UPLOAD_FOLDER, filename);
        const outputPath = path.join(UPLOAD_FOLDER, `inconsistencias_${taskId}.xlsx`);

        fs.renameSync(file.path, filepath);

        const pythonPath = path.resolve(__dirname, '..', 'venv', 'Scripts', 'python.exe');
        const scriptPath = path.resolve(__dirname, '..', 'ponto-app.py');

        const python = spawn(pythonPath, [scriptPath, taskId, filepath, outputPath]);

        python.stdout.on('data', (data) => { console.log(`[PYTHON] ${data}`); });
        python.stderr.on('data', (data) => { console.error(`[PYTHON ERROR] ${data}`); });
        python.on('error', (err) => { console.error(`[PYTHON ERRO AO INICIAR] ${err.message}`); });
        python.on('close', (code) => { console.log(`[PYTHON] Processamento finalizado com código ${code}`); });

        req.flash('success', 'Arquivo recebido! Aguarde o processamento...');
        res.redirect(`/ponto/aguarde?taskId=${taskId}`);
    } 
    catch (err) 
    {
        console.error(err);
        req.flash('error', 'Erro ao processar o arquivo.');
        return res.redirect('/ponto');
    }
});

router.get('/status/progresso/:taskId', (req, res) => 
{
    const taskId = req.params.taskId;
    const statusPath = path.join(UPLOAD_FOLDER, `status_${taskId}.json`);
    if (fs.existsSync(statusPath)) 
    {
        const status = fs.readFileSync(statusPath, 'utf-8');
        return res.json(JSON.parse(status));
    }
    return res.json({ progress: 0, message: "Aguardando início" });
});

router.get('/status/:taskId/download', (req, res) => 
{
    const taskId = req.params.taskId;
    const outputPath = path.join(UPLOAD_FOLDER, `inconsistencias_${taskId}.xlsx`);
    if (fs.existsSync(outputPath)) 
    {
        return res.download(outputPath, `inconsistencias_${taskId}.xlsx`);
    }
    req.flash('error', 'Arquivo ainda não está pronto ou houve um erro.');
    return res.redirect(`/ponto/status/${req.params.taskId}`);
});

module.exports = router;