const express = require('express');
const router = express.Router();
const employeeController = require('../controllers/employeeController');
const upload = require('../middlewares/upload');

router.get('/', employeeController.listEmployees);
router.get('/import', employeeController.showImportForm);
router.post('/import', upload.single('file'), employeeController.importEmployees);
router.get('/add', employeeController.showAddForm);
router.post('/add', employeeController.addEmployee);
router.get('/edit/:id', employeeController.showEditForm);
router.post('/edit/:id', employeeController.updateEmployee);
router.get('/delete/:id', employeeController.deleteEmployee);

module.exports = router;