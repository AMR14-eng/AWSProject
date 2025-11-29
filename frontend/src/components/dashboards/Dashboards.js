// src/components/dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LabResults from '../lab-results/LabResults';
import FileUpload from '../files/FileUpload';
import './Dashboard.css';

const Dashboard = () => {
  const { user, tenant, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('results');

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>LabCloud - {tenant?.toUpperCase()}</h1>
          <div className="user-info">
            <span>Bienvenido, {user?.username}</span>
            <button onClick={handleLogout} className="logout-button">
              Cerrar Sesión
            </button>
          </div>
        </div>
      </header>

      <nav className="dashboard-nav">
        <button 
          className={`nav-button ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          Resultados de Laboratorio
        </button>
        <button 
          className={`nav-button ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          Subir Archivos
        </button>
      </nav>

      <main className="dashboard-content">
        {activeTab === 'results' && <LabResults />}
        {activeTab === 'upload' && <FileUpload />}
      </main>
    </div>
  );
};

export default Dashboard;