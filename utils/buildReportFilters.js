const { Op } = require('sequelize');

function buildReportFilters(filter, value) 
{
    let employeeWhere = {};
    let vacationWhere = {};

    if (filter === 'contractNumber' && value) employeeWhere.contractNumber = value;

    if (filter === 'month' && value) 
    {
        const [year, month] = value.split('-');
        vacationWhere.startDate = 
        {
            [Op.between]: [
                new Date(`${year}-${month}-01`),
                new Date(`${year}-${month}-31`)
            ]
        };
    }

    if (filter === 'status' && value) vacationWhere.status = value;

    return { employeeWhere, vacationWhere };
}

module.exports = buildReportFilters;