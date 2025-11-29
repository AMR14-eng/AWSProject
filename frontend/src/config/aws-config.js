const awsConfig = {
  Auth: {
    region: 'us-east-2',
    userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_COGNITO_CLIENT_ID,
    authenticationFlowType: 'USER_PASSWORD_AUTH'
  },
  API: {
    endpoints: [
      {
        name: 'labApi',
        endpoint: process.env.REACT_APP_API_URL || 'http://localhost:5000',
        region: 'us-east-2'
      }
    ]
  }
};

export default awsConfig;