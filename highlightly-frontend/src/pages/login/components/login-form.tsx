import axios from 'axios';
import React, { useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authContext from '../../../context/auth-context';
import { LoginResponse, User } from '../interfaces/user';

const LoginForm: React.FunctionComponent<{ setAlert: (alert: string) => void }> = ({ setAlert }) => {
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [disabled, setDisabled] = useState(false);

	const { setAuthenticated } = useContext(authContext);
	const navigate = useNavigate();

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		setDisabled(true);

		axios.post<LoginResponse>("users/login/", { email: email, password: password }).then((response) => {
			localStorage.setItem("HIGHLIGHTLY_TOKEN", response.data.token);

			axios.get<User>("users/me/").then((response) => {
				setAuthenticated(response.data);
				navigate("/");
			}).catch(error => console.error(error));
		}).catch((error) => {
			if (error.response.status === 400) {
				setAlert(error.response.data.non_field_errors);
			} else {
				console.error(error);
			}
		}).finally(() => {
			setDisabled(false);
		});
	}

	return (
		<form onSubmit={handleSubmit}>
			<div className="form-group mt-3">
				<label className="text-start" htmlFor="email">Email</label>
				<input type="email" id="email" className="form-control" value={email} onChange={e => setEmail(e.target.value)} required />
			</div>

			<div className="form-group mt-3">
				<label htmlFor="password">Password</label>
				<input type="password" id="password" className="form-control" value={password}
					onChange={e => setPassword(e.target.value)} required minLength={6} />
			</div>

			<div className="mt-3 text-center">
				<button className="btn btn-lg btn-success" disabled={disabled}>Log in</button>
			</div>
		</form>
	);
};

export default LoginForm;
