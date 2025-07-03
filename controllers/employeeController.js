const ExcelJS = require('exceljs');
const { Employee } = require('../models');
const { Op } = require('sequelize');

exports.listEmployees = async (req, res) => 
{
  try 
  {
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.pageSize) || 10;
    const searchQuery = req.query.search || '';
    
    const whereClause = {};
    if (searchQuery) 
    {
      whereClause[Op.or] = [
        { name: { [Op.like]: `%${searchQuery}%` } },
        { registration: { [Op.like]: `%${searchQuery}%` } }
      ];
    }

    const offset = (page - 1) * pageSize;

    const { count, rows: employees } = await Employee.findAndCountAll({
      where: whereClause,
      limit: pageSize,
      offset: offset,
      order: [['name', 'ASC']]
    });

    const totalPages = Math.ceil(count / pageSize);

    if (page > totalPages && totalPages > 0) 
    {
      return res.redirect(`/employees?page=${totalPages}&pageSize=${pageSize}`);
    }

    res.render('employees/employees', {
      employees,
      currentPage: page,
      totalPages: totalPages,
      totalItems: count,
      pageSize: pageSize,
      searchQuery: searchQuery,
      buildPaginationUrl: (page) => buildPaginationUrl('/employees', req.query, page)
    });
  }
  catch (error) 
  {
    console.error('Erro ao listar funcionários:', error);
    res.status(500).send('Erro ao listar funcionários');
  }
};

function buildPaginationUrl(baseUrl, queryParams, page) 
{
  const params = new URLSearchParams(queryParams);
  params.set('page', page);
  return `${baseUrl}?${params.toString()}`;
}

exports.showImportForm = (req, res) => 
{
  res.render('employees/import');
};

exports.importEmployees = async (req, res) => 
{
  try 
  {
    co
    nsole.log('req.file:', req.file);
    console.log('req.body:', req.body);

    if (!req.file) return res.status(400).send('Nenhum arquivo enviado.');

    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.readFile(req.file.path);
    const worksheet = workbook.getWorksheet(1);

    const employees = [];
    worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => 
    {
      if (rowNumber > 2) 
      {
        employees.push({
          registration: row.getCell(1).value,
          name: row.getCell(2).value,
          admissionDate: parseDate(row.getCell(3).value),
          absenceDays: row.getCell(6)?.value || 0,
          lastVacationDate: parseDate(row.getCell(7).value),
          maxVacationDate: parseDate(row.getCell(9).value),
          vacationDays: row.getCell(12).value || 30,
          branchName: row.getCell(13).value,
          category: row.getCell(15).value,
          contractNumber: row.getCell(16).value,
          local: row.getCell(17).value,
          absence: row.getCell(19).value,
        });
      }
    });

    await Employee.bulkCreate(employees, { 
        validate: true,
        updateOnDuplicate: [
            'category',
            'contractNumber',
            'branchName',
            'admissionDate',
            'lastVacationDate',
            'vacationDays',
            'maxVacationDate',
            'absenceDays',
            'local',
            'absence'
          ]
    });
    
    res.redirect('/employees');
  } 
  catch (error) 
  {
    console.error(error);
    res.status(500).send('Erro ao importar funcionários');
  }
};

exports.showAddForm = (req, res) => 
{
  res.render('employees/add');
};

exports.addEmployee = async (req, res) => 
{
  try 
  {
    const { registration, name, category, contractNumber, branchName, admissionDate, lastVacationDate, vacationDays, maxVacationDate, absenceDays, isEligible, local } = req.body;

    const existingEmployee = await Employee.findOne({ where: { registration } });
    
    if (existingEmployee) 
    {
      return res.status(400).render('employees/add', {
        error: 'Já existe um funcionário com esta matrícula',
        formData: req.body
      });
    }

    await Employee.create({
      registration,
      name,
      category,
      contractNumber,
      branchName,
      admissionDate: admissionDate,
      lastVacationDate: lastVacationDate || null,
      vacationDays: parseInt(vacationDays),
      maxVacationDate: maxVacationDate || null,
      absenceDays: parseInt(absenceDays),
      isEligible: isEligible === 'true' || isEligible === true,
      local,
      createdAt: new Date(),
      updatedAt: new Date()
    });

    res.redirect('/employees');
  } 
  catch (error) 
  {
    console.error('Erro ao criar funcionário:', error);
    res.status(500).send('Erro ao criar funcionário');
  }
};

exports.showEditForm = async (req, res) => 
{
  try 
  {
    const employee = await Employee.findByPk(req.params.id);
    if (!employee) return res.status(404).send('Funcionário não encontrado');

    res.render('employees/edit', { employee });
  } 
  catch (error) 
  {
    console.error('Erro ao carregar funcionário:', error);
    res.status(500).send('Erro ao carregar funcionário');
  }
};

exports.updateEmployee = async (req, res, next) => 
{
  try 
  {
    const { registration, name, category, contractNumber, branchName, admissionDate, lastVacationDate, vacationDays, maxVacationDate, absenceDays, absence, isEligible, local } = req.body;
    
    const { id } = req.params;

    const hasRescisao = absence && absence.includes("RESCISÃO SEM JUSTA CAUSA POR INICIATIVA DO EMPREGADOR");
    const eligibility = hasRescisao ? false : (isEligible === 'true' || isEligible === true);

    await Employee.update({
      registration,
      name,
      category,
      contractNumber,
      branchName,
      admissionDate: admissionDate,
      lastVacationDate: lastVacationDate || null,
      vacationDays: parseInt(vacationDays),
      maxVacationDate: maxVacationDate || null,
      absenceDays: parseInt(absenceDays),
      absence: absence,
      isEligible: eligibility,
      local
    }, {
      where: { id }
    });

    res.redirect('/employees');
  } 
  catch (error) 
  {
    console.error('Erro ao atualizar funcionário:', error);
    next(error);
  }
};

exports.deleteEmployee = async (req, res) => 
{
  try 
  {
    const { id } = req.params;

    const deleted = await Employee.destroy({
      where: { id }
    });

    if (deleted) res.redirect('/employees');
    else res.status(404).send('Funcionário não encontrado');
  } 
  catch (error) 
  {
    console.error('Erro ao deletar funcionário:', error);
    res.status(500).send('Erro ao deletar funcionário');
  }
};

function parseDate(value) 
{
  if (!value || typeof value !== 'string') return null;

  const [day, month, year] = value.split('/');
  if (!day || !month || !year) return null;

  const isoDate = new Date(`${year}-${month}-${day}`);
  return isNaN(isoDate.getTime()) ? null : isoDate;
}