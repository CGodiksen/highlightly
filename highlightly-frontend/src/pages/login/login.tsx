import React from 'react';
import AuthenticationBase from './components/authentication-base';
import LoginForm from './components/login-form';

const LoginPage: React.FunctionComponent<{}> = () => {
	return (
		<AuthenticationBase title="Log in" Form={LoginForm} />
	);
}

export default LoginPage;