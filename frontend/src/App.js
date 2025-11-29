// src/App.js
import React from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './components/auth/Login';
import Dashboard from './components/dashboard/Dashboard';
import { Amplify } from 'aws-amplify';
import awsConfig from './config/aws-config';
import './App.css';

Amplify.configure(awsConfig);

const AppContent = () => {
  const { isAuthenticated, loading, tenant } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="App">
      {!isAuthenticated ? <Login /> : <Dashboard />}
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;