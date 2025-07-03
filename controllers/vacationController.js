const { Employee, Vacation } = require('../models');
const ExcelJS = require('exceljs');
const moment = require('moment');
const { Op, fn, col, Sequelize } = require('sequelize');
const buildReportFilters = require('../utils/buildReportFilters');

exports.listVacations = async (req, res) => 
{
  try 
  {
    const { search, status, page = 1, pageSize = 10 } = req.query;

    let where = {};
    let employeeWhere = {};

    if (search) 
    {
      employeeWhere[Op.or] = [
        { name: { [Op.like]: `%${search}%` } },
        { registration: { [Op.like]: `%${search}%` } },
      ];
    }

    if (status && status !== 'all') where.status = status;

    const pageNumber = parseInt(page, 10);
    const pageSizeNumber = parseInt(pageSize, 10);

    const offset = (pageNumber - 1) * pageSizeNumber;

    const { count: totalItems, rows: vacations } = await Vacation.findAndCountAll({
      where,
      include: [{
        model: Employee,
        where: employeeWhere,
        required: true,
      }],
      order: [['startDate', 'ASC']],
      limit: pageSizeNumber,
      offset,
    });

    const totalPages = Math.ceil(totalItems / pageSizeNumber);

    res.render('vacations/vacations', {
      vacations,
      searchQuery: search || '',
      currentStatus: status || 'all',
      currentPage: pageNumber,
      pageSize: pageSizeNumber,
      totalPages,
      totalItems,
        buildPaginationUrl: (page) => buildPaginationUrl('/vacations', req.query, page)
    });
  } 
  catch (error) 
  {
    console.error('Erro ao listar férias:', error);
    res.status(500).send('Erro ao listar férias');
  }
};

function buildPaginationUrl(baseUrl, queryParams, page) 
{
  const params = new URLSearchParams(queryParams);
  params.set('page', page);
  return `${baseUrl}?${params.toString()}`;
}

exports.showDistributionForm = async (req, res) => 
{
  try 
  {
    const vacations = await Vacation.findAll({
      include: [Employee],
    });

    res.render('vacations/distribute', { vacations });
  } 
  catch (error) 
  {
    console.error('Erro ao exibir distribuição de férias:', error);
    res.status(500).send('Erro ao exibir distribuição de férias');
  }
};

exports.distributeVacations = async (req, res) => 
{
  try 
  {
    const eligibleEmployees = await Employee.findAll({
      where: { isEligible: true },
    });

    eligibleEmployees.sort((a, b) => new Date(a.admissionDate) - new Date(b.admissionDate));

    const months = 12;
    const employeesPerMonth = Math.ceil(eligibleEmployees.length / months);

    const currentYear = new Date().getFullYear();
    let monthIndex = 0;

    for (let i = 0; i < eligibleEmployees.length; i++) 
    {
      const employee = eligibleEmployees[i];
      if (i > 0 && i % employeesPerMonth === 0) monthIndex++;

      let startDate = new Date(currentYear, monthIndex, 1);
      let endDate = new Date(startDate);
      endDate.setDate(endDate.getDate() + employee.vacationDays - 1);

      const deadline = new Date(employee.maxVacationDate);
      if (deadline)
      {
        if (endDate > deadline) 
        {
          startDate = new Date(deadline);
          startDate.setDate(startDate.getDate() - employee.vacationDays + 1);
          endDate = new Date(deadline);
        }
      }

      if (startDate < new Date(currentYear, 0, 1)) 
      {
        startDate = new Date(currentYear, 0, 1);
        endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + employee.vacationDays - 1);
      }

      const existingVacation = await Vacation.findOne({
        where: {
          employeeId: employee.id,
          [Op.and]: [
            Sequelize.where(fn('YEAR', col('startDate')), currentYear),
          ],
        },
      });

      if (existingVacation) 
      {
        await existingVacation.update({
          startDate,
          endDate,
          days: employee.vacationDays,
          status: 'pending',
        });
      } 
      else 
      {
        await Vacation.create({
          employeeId: employee.id,
          startDate,
          endDate,
          days: employee.vacationDays,
          status: 'pending',
        });
      }
    }

    res.redirect('/vacations');
  } 
  catch (error) 
  {
    console.error('Erro ao distribuir férias:', error);
    res.status(500).send('Erro ao distribuir férias');
  }
};

exports.showReportForm = async (req, res) => 
{
  try 
  {
    const { filter, value } = req.query;
    const { employeeWhere, vacationWhere } = buildReportFilters(filter, value);

    const employees = await Employee.findAll({
      include: [{
        model: Vacation,
        required: true,
        where: vacationWhere
      }],
      where: employeeWhere
    });

    res.render('vacations/report', {employees, filter, value});
  } 
  catch (error) 
  {
    console.error(error);
    res.status(500).send('Erro ao exibir relatório de férias');
  }
};

exports.generateReport = async (req, res) => 
{
  try 
  {
    const { filter, value } = req.query;
    const { employeeWhere, vacationWhere } = buildReportFilters(filter, value);
    
    const employees = await Employee.findAll({
      include: [{
        model: Vacation,
        required: true,
        where: vacationWhere
      }],
      where: employeeWhere
    });

    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Férias');
    
    worksheet.columns = [
      { header: 'Matrícula', key: 'registration', width: 15 },
      { header: 'Nome', key: 'name', width: 30 },
      { header: 'Categoria', key: 'category', width: 15 },
      { header: 'Contrato', key: 'contractNumber', width: 30 },
      { header: 'Razão Social Filial', key: 'branchName', width: 20 },
      { header: 'Data de Admissão', key: 'admissionDate', width: 20 },
      { header: 'Início das Férias', key: 'startDate', width: 20 },
      { header: 'Fim das Férias', key: 'endDate', width: 20 },
      { header: 'Quantidade de Dias', key: 'days', width: 20 }
    ];

    employees.forEach(employee => {
      employee.Vacations.forEach(vacation => {
        worksheet.addRow({
          registration: employee.registration,
          name: employee.name,
          category: employee.category,
          contractNumber: employee.contractNumber,
          branchName: employee.branchName,
          admissionDate: moment(employee.admissionDate).format('DD/MM/YYYY'),
          startDate: moment(vacation.startDate).format('DD/MM/YYYY'),
          endDate: moment(vacation.endDate).format('DD/MM/YYYY'),
          days: vacation.days
        });
      });
    });

    res.setHeader(
      'Content-Type',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    );
    res.setHeader(
      'Content-Disposition',
      'attachment; filename=relatorio_ferias.xlsx'
    );

    await workbook.xlsx.write(res);
    res.end();
  } 
  catch (error) 
  {
    console.error(error);
    res.status(500).send('Erro ao gerar relatório');
  }
};

exports.approveVacation = async (req, res) => 
{
  try 
  {
    const vacationId = req.params.id;
    await Vacation.update(
      { status: 'approved' },
      { where: { id: vacationId } }
    );

    res.redirect('/vacations');
  } 
  catch (error) 
  {
    console.error('Erro ao aprovar férias:', error);
    res.status(500).send('Erro ao aprovar férias');
  }
};

exports.rejectVacation = async (req, res) => 
{
  try 
  {
    const vacationId = req.params.id;
    await Vacation.update(
      { status: 'rejected' },
      { where: { id: vacationId } }
    );

    res.redirect('/vacations');
  } 
  catch (error) 
  {
    console.error('Erro ao rejeitar férias:', error);
    res.status(500).send('Erro ao rejeitar férias');
  }
};

exports.approveAllVacation = async (req, res) => 
{
  try 
  {
    await Vacation.update(
      { status: 'approved' },
      { where: { status: 'pending' } }
    );
    
    res.redirect('/vacations');
  } 
  catch (error) 
  {
    console.error('Erro ao aprovar férias:', error);
    res.status(500).send('Erro ao aprovar férias');
  }
};

exports.showEditForm = async (req, res) => 
{
  try 
  {
    const vacation = await Vacation.findByPk(req.params.id, {
      include: Employee
    });

    if (!vacation) return res.status(404).send('Férias não encontradas');

    res.render('vacations/edit', { vacation });
  } 
  catch (error) 
  {
    console.error('Erro ao buscar férias para edição:', error);
    res.status(500).send('Erro ao buscar férias');
  }
};

exports.updateVacation = async (req, res) => 
{
  try 
  {
    const { startDate, endDate, days, status } = req.body;
    await Vacation.update(
      { startDate, endDate, days, status },
      { where: { id: req.params.id } }
    );

    res.redirect('/vacations');
  } 
  catch (error) 
  {
    console.error('Erro ao atualizar férias:', error);
    res.status(500).send('Erro ao atualizar férias');
  }
};

exports.deleteVacation = async (req, res) => {
  try 
  {
    const { id } = req.params;

    const deleted = await Vacation.destroy({
      where: { id }
    });

    if (deleted) res.redirect('/vacations');
    else res.status(404).send('Férias não encontrada');
  } 
  catch (error) 
  {
    console.error('Erro ao deletar férias:', error);
    res.status(500).send('Erro ao deletar férias');
  }
};