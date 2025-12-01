// app.js
// Configuración de Cognito
const poolData = {
    UserPoolId: 'us-east-2_Wi7VHkSWm', 
    ClientId: '4f542vcmv892f5nlpjh6ve8b1v' 
};

const userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);
const API_URL = 'http://3.137.123.210:5000';

let currentUser = null;
let currentSession = null;
let currentTenant = null;

// ==================== FUNCIONES DE AUTENTICACIÓN ====================

async function loginWithCognito(username, password) {
    console.log('🔐 Intentando login con:', username);
    try {
        const authenticationData = {
            Username: username,
            Password: password,
        };
        
        const authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(authenticationData);
        
        const userData = {
            Username: username,
            Pool: userPool
        };
        
        const cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);
        
        return new Promise((resolve, reject) => {
            cognitoUser.authenticateUser(authenticationDetails, {
                onSuccess: function (result) {
                    console.log('✅ Login exitoso', result);
                    currentSession = result;
                    currentUser = cognitoUser;
                    
                    // Obtener los atributos del usuario para sacar el tenant_id
                    cognitoUser.getUserAttributes(function(err, attributes) {
                        if (err) {
                            console.error('❌ Error obteniendo atributos:', err);
                            reject(err);
                            return;
                        }
                        
                        console.log('Atributos del usuario:', attributes);
                        
                        // Buscar el tenant_id en los atributos
                        const tenantAttr = attributes.find(attr => attr.getName() === 'custom:tenant_id');
                        currentTenant = tenantAttr ? tenantAttr.getValue() : 'unknown';
                        console.log('Tenant ID encontrado:', currentTenant);
                        
                        resolve({
                            user: cognitoUser,
                            session: result,
                            tenant: currentTenant,
                            needsPasswordChange: false
                        });
                    });
                },
                onFailure: function(err) {
                    console.error('❌ Error en login:', err);
                    reject(err);
                },
                newPasswordRequired: function(userAttributes, requiredAttributes) {
                    console.log('🔐 Nueva contraseña requerida - Cambiando a pantalla de cambio');
                    
                    resolve({
                        needsPasswordChange: true,
                        user: cognitoUser,
                        userAttributes: userAttributes,
                        requiredAttributes: requiredAttributes
                    });
                }
            });
        });
        
    } catch (error) {
        console.error('❌ Error general en login:', error);
        throw error;
    }
}

async function completeNewPassword() {
    const newPassword = document.getElementById('newPassword').value;
    
    if (!newPassword) {
        showError('changePasswordError', 'Por favor ingresa una nueva contraseña');
        return;
    }

    if (newPassword.length < 8) {
        showError('changePasswordError', 'La contraseña debe tener al menos 8 caracteres');
        return;
    }

    // Limpiar errores
    document.getElementById('changePasswordError').classList.add('hidden');

    console.log('Completando cambio de contraseña...');
    
    currentUser.completeNewPasswordChallenge(newPassword, {}, {
        onSuccess: function(result) {
            console.log('✅ Contraseña cambiada exitosamente');
            currentSession = result;
            
            // Obtener tenant_id después del cambio de contraseña
            currentUser.getUserAttributes(function(err, attributes) {
                if (err) {
                    console.error('Error obteniendo atributos:', err);
                    showError('changePasswordError', 'Error obteniendo información del usuario');
                    return;
                }
                
                const tenantAttr = attributes.find(attr => attr.getName() === 'custom:tenant_id');
                currentTenant = tenantAttr ? tenantAttr.getValue() : 'unknown';
                console.log('Tenant después de cambio de contraseña:', currentTenant);
                
                // Mostrar dashboard
                showDashboard(currentTenant);
            });
        },
        onFailure: function(err) {
            console.error('❌ Error cambiando contraseña:', err);
            let errorMsg = 'Error cambiando contraseña: ' + err.message;
            
            if (err.message.includes('Password does not conform')) {
                errorMsg = 'La contraseña no cumple los requisitos. Debe tener mayúsculas, minúsculas, números y al menos 8 caracteres.';
            }
            
            showError('changePasswordError', errorMsg);
        }
    });
}

// ==================== FUNCIONES DE NAVEGACIÓN ====================

function showRegister() {
    console.log('📋 Mostrando pantalla de registro');
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('registerPrompt').classList.add('hidden');
    document.getElementById('registerScreen').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('changePasswordScreen').classList.add('hidden');
}

function showLogin() {
    console.log('🔙 Volviendo a pantalla de login');
    document.getElementById('registerScreen').classList.add('hidden');
    document.getElementById('loginScreen').classList.remove('hidden');
    document.getElementById('registerPrompt').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('changePasswordScreen').classList.add('hidden');
    document.getElementById('registerError').classList.add('hidden');
    document.getElementById('registerResult').classList.add('hidden');
    document.getElementById('registerForm').reset();
}

function showDashboard(tenantId) {
    console.log('🎯 Mostrando dashboard para tenant:', tenantId);
    try {
        // Ocultar todas las pantallas de login/registro
        document.getElementById('loginScreen').classList.add('hidden');
        document.getElementById('changePasswordScreen').classList.add('hidden');
        document.getElementById('registerScreen').classList.add('hidden');
        document.getElementById('registerPrompt').classList.add('hidden');
        
        // Mostrar dashboard
        document.getElementById('dashboard').classList.remove('hidden');
        
        const tenantName = tenantId === 'laba' ? 'Laboratorio A' : 
                          tenantId === 'labb' ? 'Laboratorio B' : 
                          tenantId.charAt(0).toUpperCase() + tenantId.slice(1);
        
        document.getElementById('tenantName').textContent = tenantName;
        console.log('✅ Dashboard mostrado correctamente');
        
        // Mostrar sección de facturación
        const billingSection = document.getElementById('billingSection');
        if (billingSection) {
            billingSection.classList.remove('hidden');
        }
        
        // Mostrar sección para crear resultados
        const createResultSection = document.getElementById('createResultSection');
        if (createResultSection) {
            createResultSection.classList.remove('hidden');
        }
        
        // Mensaje de bienvenida
        document.getElementById('resultsList').innerHTML = `
            <div class="success">
                <h4>✅ ¡Bienvenido a LabCloud!</h4>
                <p><strong>Tenant:</strong> ${tenantName}</p>
                <p><strong>Usuario:</strong> ${currentUser ? currentUser.username : 'N/A'}</p>
                <p><strong>Rol:</strong> Administrador</p>
                <p><em>Use el formulario abajo para crear nuevos resultados.</em></p>
            </div>
        `;
        
    } catch (error) {
        console.error('❌ Error en showDashboard:', error);
    }
}

// ==================== FUNCIONES DE REGISTRO ====================

async function registerNewTenant() {
    const companyName = document.getElementById('companyName').value;
    const contactName = document.getElementById('contactName').value;
    const email = document.getElementById('registerEmail').value;
    const phone = document.getElementById('phone').value;
    const tier = document.getElementById('subscriptionTier').value;
    
    // Validaciones básicas
    if (!companyName || !contactName || !email || !tier) {
        showError('registerError', 'Por favor complete todos los campos requeridos');
        return;
    }
    
    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showError('registerError', 'Por favor ingrese un email válido');
        return;
    }
    
    // Deshabilitar botón durante el registro
    const registerBtn = document.getElementById('registerBtn');
    registerBtn.disabled = true;
    registerBtn.textContent = 'Registrando...';
    
    try {
        const response = await fetch(`${API_URL}/api/public/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company_name: companyName,
                contact_name: contactName,
                email: email,
                phone: phone,
                subscription_tier: tier
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('registerResult').innerHTML = `
                <div class="success">
                    <h4>✅ ¡Registro Exitoso!</h4>
                    <p><strong>ID de Tenant:</strong> ${data.tenant_id}</p>
                    <p><strong>Usuario:</strong> ${data.email}</p>
                    <p><strong>Contraseña Temporal:</strong> <code>${data.temp_password || 'Enviada por email'}</code></p>
                    <p><strong>Nota:</strong> ${data.note}</p>
                    <p>Guarde estas credenciales en un lugar seguro.</p>
                    <button onclick="showLogin()" class="action-btn">Ir a Login</button>
                </div>
            `;
            document.getElementById('registerResult').classList.remove('hidden');
            document.getElementById('registerForm').reset();
        } else {
            showError('registerError', data.message || 'Error en el registro');
        }
    } catch (error) {
        showError('registerError', `Error de conexión: ${error.message}`);
    } finally {
        registerBtn.disabled = false;
        registerBtn.textContent = 'Registrarse';
    }
}

// ==================== FUNCIONES DE RESULTADOS ====================

async function loadResults(patientId = null) {
    try {
        let url = `${API_URL}/api/v1/results`;
        if (patientId) {
            url = `${API_URL}/api/v1/results/${patientId}`;
        }
        
        console.log('📡 Haciendo request a:', url);
        
        // Obtener el token JWT de la sesión de Cognito
        const idToken = currentSession?.getIdToken()?.getJwtToken();
        
        const headers = {
            'X-Tenant-Id': currentTenant
        };
        
        // Agregar Authorization header si hay token
        if (idToken) {
            headers['Authorization'] = `Bearer ${idToken}`;
        }
        
        console.log('🔑 Headers:', headers);
        
        const response = await fetch(url, { headers });
        
        console.log('📋 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        console.log('✅ Datos recibidos:', data);
        displayResults(data.results || []);
    } catch (error) {
        console.error('❌ Error cargando resultados:', error);
        document.getElementById('resultsList').innerHTML = 
            `<div class="error">Error cargando resultados: ${error.message}</div>`;
    }
}

function displayResults(results) {
    const container = document.getElementById('resultsList');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<p>No se encontraron resultados.</p>';
        return;
    }
    
    container.innerHTML = results.map(result => `
        <div class="result-item">
            <strong>ID Resultado:</strong> ${result.id}<br>
            <strong>Paciente:</strong> ${result.patient_id || 'N/A'}<br>
            <strong>Prueba:</strong> ${result.test_code}<br>
            <strong>Fecha:</strong> ${new Date(result.created_at).toLocaleDateString()}<br>
            <strong>Datos:</strong> <pre>${JSON.stringify(result.test_data, null, 2)}</pre>
        </div>
    `).join('');
}

async function createLabResult() {
    const patientId = document.getElementById('newPatientId').value;
    const testCode = document.getElementById('testCode').value;
    const testDataStr = document.getElementById('testData').value;
    
    if (!patientId || !testCode) {
        showStatus('createResultStatus', 'ID de paciente y código de prueba son requeridos', 'error');
        return;
    }
    
    let testData;
    try {
        testData = testDataStr ? JSON.parse(testDataStr) : {};
    } catch (e) {
        showStatus('createResultStatus', 'Datos JSON inválidos. Use formato: {"campo": "valor"}', 'error');
        return;
    }
    
    try {
        const idToken = currentSession?.getIdToken()?.getJwtToken();
        const response = await fetch(`${API_URL}/api/v1/results`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${idToken}`,
                'X-Tenant-Id': currentTenant
            },
            body: JSON.stringify({
                patient_id: patientId,
                test_code: testCode,
                test_data: testData
            })
        });
        
        if (!response.ok) throw new Error(`Error ${response.status}`);
        
        const data = await response.json();
        
        showStatus('createResultStatus', 
            `✅ Resultado creado exitosamente (ID: ${data.id})`, 
            'success');
        
        // Limpiar formulario
        document.getElementById('newPatientId').value = '';
        document.getElementById('testCode').value = '';
        document.getElementById('testData').value = '';
        
        // Recargar resultados si estamos viendo este paciente
        if (document.getElementById('patientId').value === patientId) {
            loadResults(patientId);
        }
        
    } catch (error) {
        showStatus('createResultStatus', `Error creando resultado: ${error.message}`, 'error');
    }
}

function searchResults() {
    const patientId = document.getElementById('patientId').value;
    loadResults(patientId);
}

// ==================== FUNCIONES DE FACTURACIÓN ====================

async function loadBillingInfo() {
    try {
        const idToken = currentSession?.getIdToken()?.getJwtToken();
        const response = await fetch(`${API_URL}/api/v1/admin/billing`, {
            headers: {
                'Authorization': `Bearer ${idToken}`,
                'X-Tenant-Id': currentTenant
            }
        });
        
        if (!response.ok) throw new Error(`Error ${response.status}: ${await response.text()}`);
        
        const data = await response.json();
        displayBillingInfo(data);
    } catch (error) {
        document.getElementById('billingInfo').innerHTML = 
            `<div class="error">Error cargando facturación: ${error.message}</div>`;
    }
}

function displayBillingInfo(billingData) {
    const invoice = billingData.current_invoice;
    
    if (!invoice) {
        document.getElementById('billingInfo').innerHTML = 
            '<p>No hay información de facturación disponible para este mes.</p>';
        return;
    }
    
    let html = `
        <div class="result-item">
            <h4>📄 Factura ${invoice.month}</h4>
            <p><strong>Empresa:</strong> ${invoice.company_name}</p>
            <p><strong>Plan:</strong> ${invoice.subscription_tier.toUpperCase()}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Descripción</th>
                        <th style="text-align: right;">Cantidad</th>
                        <th style="text-align: right;">Precio Unitario</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    invoice.items.forEach(item => {
        if (item) {
            html += `
                <tr>
                    <td>${item.description}</td>
                    <td style="text-align: right;">${item.quantity}</td>
                    <td style="text-align: right;">$${item.unit_price.toFixed(2)}</td>
                    <td style="text-align: right;">$${item.total.toFixed(2)}</td>
                </tr>
            `;
        }
    });
    
    html += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="3" style="text-align: right;"><strong>Subtotal:</strong></td>
                        <td style="text-align: right;">$${invoice.subtotal.toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td colspan="3" style="text-align: right;"><strong>Impuestos (16%):</strong></td>
                        <td style="text-align: right;">$${invoice.tax.toFixed(2)}</td>
                    </tr>
                    <tr style="background: #e9ecef;">
                        <td colspan="3" style="text-align: right;"><strong>Total:</strong></td>
                        <td style="text-align: right; font-weight: bold;">$${invoice.total.toFixed(2)}</td>
                    </tr>
                </tfoot>
            </table>
            
            <p><strong>Fecha de Vencimiento:</strong> ${new Date(invoice.due_date).toLocaleDateString()}</p>
            <button onclick="downloadInvoice('${invoice.month}')" class="action-btn secondary">
                Descargar Factura (PDF)
            </button>
        </div>
    `;
    
    document.getElementById('billingInfo').innerHTML = html;
}

async function loadUsageHistory() {
    try {
        const idToken = currentSession?.getIdToken()?.getJwtToken();
        const response = await fetch(`${API_URL}/api/v1/admin/billing`, {
            headers: {
                'Authorization': `Bearer ${idToken}`,
                'X-Tenant-Id': currentTenant
            }
        });
        
        if (!response.ok) throw new Error(`Error ${response.status}`);
        
        const data = await response.json();
        displayUsageHistory(data.usage_summary || []);
    } catch (error) {
        document.getElementById('usageHistory').innerHTML = 
            `<div class="error">Error cargando historial: ${error.message}</div>`;
    }
}

function displayUsageHistory(usageData) {
    if (!usageData || usageData.length === 0) {
        document.getElementById('usageHistory').innerHTML = 
            '<p>No hay historial de uso disponible.</p>';
        return;
    }
    
    let html = `
        <div class="result-item">
            <h4>📊 Historial de Uso</h4>
            <table>
                <thead>
                    <tr>
                        <th>Mes</th>
                        <th style="text-align: right;">Resultados</th>
                        <th style="text-align: right;">Llamadas API</th>
                        <th style="text-align: right;">Almacenamiento (GB)</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    usageData.forEach(item => {
        html += `
            <tr>
                <td>${item.month}</td>
                <td style="text-align: right;">${item.results_processed.toLocaleString()}</td>
                <td style="text-align: right;">${item.api_calls.toLocaleString()}</td>
                <td style="text-align: right;">${item.storage_gb?.toFixed(2) || '0.00'}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    document.getElementById('usageHistory').innerHTML = html;
    document.getElementById('usageHistory').classList.remove('hidden');
}

function downloadInvoice(month) {
    alert(`La descarga de factura para ${month} estaría disponible en una implementación completa.`);
    // En producción: window.open(`${API_URL}/api/v1/admin/billing/invoice/${month}/pdf`);
}

// ==================== FUNCIONES DE ARCHIVOS ====================

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('uploadStatus', 'Por favor selecciona un archivo', 'error');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const idToken = currentSession?.getIdToken()?.getJwtToken();
        
        const response = await fetch(`${API_URL}/api/v1/upload`, {
            method: 'POST',
            headers: {
                'X-Tenant-Id': currentTenant,
                'Authorization': `Bearer ${idToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Error subiendo archivo');
        }
        
        const data = await response.json();
        showStatus('uploadStatus', `✅ Archivo subido exitosamente! URI: ${data.s3_uri}`, 'success');
        fileInput.value = '';
    } catch (error) {
        showStatus('uploadStatus', `❌ Error: ${error.message}`, 'error');
    }
}

// ==================== FUNCIONES UTILITARIAS ====================

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.classList.remove('hidden');
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="${type}">${message}</div>`;
}

function logout() {
    if (currentUser) {
        currentUser.signOut();
    }
    currentUser = null;
    currentSession = null;
    currentTenant = null;
    
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('loginScreen').classList.remove('hidden');
    document.getElementById('registerPrompt').classList.remove('hidden');
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').classList.add('hidden');
    
    console.log('👋 Sesión cerrada');
}

function showTerms() {
    alert('Términos y condiciones:\n\n1. Uso autorizado solo para personal médico.\n2. Protección de datos garantizada.\n3. Facturación mensual según uso.\n\nContacto: soporte@labcloud.com');
}

// ==================== EVENT LISTENERS ====================

document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    console.log('📝 Formulario de login enviado');
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // Limpiar errores anteriores
    document.getElementById('loginError').classList.add('hidden');
    
    try {
        const result = await loginWithCognito(username, password);
        console.log('🔍 Resultado del login:', result);
        
        if (result.needsPasswordChange) {
            console.log('🔐 MOSTRANDO pantalla de cambio de contraseña');
            currentUser = result.user;
            document.getElementById('loginScreen').classList.add('hidden');
            document.getElementById('registerPrompt').classList.add('hidden');
            document.getElementById('changePasswordScreen').classList.remove('hidden');
            console.log('✅ Pantalla de cambio de contraseña ACTIVADA');
        } else {
            console.log('✅ Login normal - mostrando dashboard');
            showDashboard(result.tenant);
        }
    } catch (error) {
        console.error('❌ Error en proceso de login:', error);
        showError('loginError', 'Error de login: ' + error.message);
    }
});

document.getElementById('registerForm').addEventListener('submit', function(e) {
    e.preventDefault();
    registerNewTenant();
});

// ==================== INICIALIZACIÓN ====================

console.log('✅ LabCloud Frontend cargado - Sistema completo');
console.log('📞 API URL:', API_URL);
console.log('👤 User Pool ID:', poolData.UserPoolId);