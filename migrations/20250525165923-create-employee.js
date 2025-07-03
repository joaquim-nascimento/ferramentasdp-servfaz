'use strict';
/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('Employees', {
      id: {
        allowNull: false,
        autoIncrement: true,
        primaryKey: true,
        type: Sequelize.INTEGER
      },
      name: {
        type: Sequelize.STRING
      },
      admissionDate: {
        type: Sequelize.DATE
      },
      registration: {
        type: Sequelize.STRING
      },
      workplace: {
        type: Sequelize.STRING
      },
      contractNumber: {
        type: Sequelize.STRING
      },
      lastVacationDate: {
        type: Sequelize.DATE
      },
      vacationDays: {
        type: Sequelize.INTEGER
      },
      professionalCategory: {
        type: Sequelize.STRING
      },
      workSchedule: {
        type: Sequelize.STRING
      },
      absenceDays: {
        type: Sequelize.INTEGER
      },
      isEligible: {
        type: Sequelize.BOOLEAN
      },
      createdAt: {
        allowNull: false,
        type: Sequelize.DATE
      },
      updatedAt: {
        allowNull: false,
        type: Sequelize.DATE
      }
    });
  },
  async down(queryInterface, Sequelize) {
    await queryInterface.dropTable('Employees');
  }
};