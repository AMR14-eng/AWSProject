import React, { createContext, useState, useContext, useEffect } from 'react';
import { Auth } from 'aws-amplify';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await Auth.currentAuthenticatedUser();
      const userAttributes = await Auth.currentUserInfo();
      
      // Obtener tenant_id del atributo personalizado
      const tenantId = userAttributes.attributes['custom:tenant_id'];
      
      setUser(currentUser);
      setTenant(tenantId);
      console.log('Usuario autenticado:', currentUser.username, 'Tenant:', tenantId);
    } catch (error) {
      setUser(null);
      setTenant(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const user = await Auth.signIn(username, password);
      const userAttributes = await Auth.currentUserInfo();
      const tenantId = userAttributes.attributes['custom:tenant_id'];
      
      setUser(user);
      setTenant(tenantId);
      
      return { success: true, tenant: tenantId };
    } catch (error) {
      console.error('Error en login:', error);
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      await Auth.signOut();
      setUser(null);
      setTenant(null);
    } catch (error) {
      console.error('Error en logout:', error);
    }
  };

  const value = {
    user,
    tenant,
    loading,
    login,
    logout,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};