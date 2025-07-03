const express = require('express');
const router = express.Router();
const vacationController = require('../controllers/vacationController');

router.get('/', vacationController.listVacations);
router.get('/distribute', vacationController.showDistributionForm);
router.post('/distribute', vacationController.distributeVacations);
router.get('/report', vacationController.showReportForm);
router.get('/report/export', vacationController.generateReport);
router.get('/approve/:id', vacationController.approveVacation);
router.get('/reject/:id', vacationController.rejectVacation);
router.get('/approveAll', vacationController.approveAllVacation);
router.get('/edit/:id', vacationController.showEditForm);
router.post('/edit/:id', vacationController.updateVacation);
router.get('/delete/:id', vacationController.deleteVacation);

module.exports = router;