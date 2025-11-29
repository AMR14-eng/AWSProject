// src/services/api.js
import { Auth } from 'aws-amplify';

class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  }

  async getHeaders() {
    try {
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      
      return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Tenant-Id': await this.getCurrentTenant()
      };
    } catch (error) {
      console.error('Error getting auth token:', error);
      throw error;
    }
  }

  async getCurrentTenant() {
    try {
      const user = await Auth.currentAuthenticatedUser();
      const attributes = await Auth.currentUserInfo();
      return attributes.attributes['custom:tenant_id'];
    } catch (error) {
      console.error('Error getting tenant:', error);
      throw error;
    }
  }

  async getLabResults(patientId = null) {
    try {
      const headers = await this.getHeaders();
      const url = patientId 
        ? `${this.baseURL}/api/v1/results/${patientId}`
        : `${this.baseURL}/api/v1/results`;
      
      const response = await fetch(url, { headers });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching lab results:', error);
      throw error;
    }
  }

  async createLabResult(resultData) {
    try {
      const headers = await this.getHeaders();
      
      const response = await fetch(`${this.baseURL}/api/v1/results`, {
        method: 'POST',
        headers,
        body: JSON.stringify(resultData)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error creating lab result:', error);
      throw error;
    }
  }

  async uploadFile(file) {
    try {
      const headers = await this.getHeaders();
      const formData = new FormData();
      formData.append('file', file);
      
      // Cambiar Content-Type para FormData
      delete headers['Content-Type'];
      
      const response = await fetch(`${this.baseURL}/api/v1/upload`, {
        method: 'POST',
        headers,
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error uploading file:', error);
      throw error;
    }
  }
}

export default new ApiService();