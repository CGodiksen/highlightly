import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import routes from './shared/data/routes';
import authContext from './context/auth-context';
import { User } from './pages/login/interfaces/user';
import Navbar from './shared/components/navbar';
import axios from 'axios';
import './shared/shared.css';
import { Toaster } from 'react-hot-toast';

export const baseURL = "127.0.0.1:8000";

const App: React.FunctionComponent<{}> = () => {
	const [authenticated, setAuthenticated] = useState<User | null>(null);

	// Add a request interceptor to add the token before the request is sent to the API.
	axios.interceptors.request.use(function (axiosConfig) {
		const token = localStorage.getItem("HIGHLIGHTLY_TOKEN") || "";
		if (token !== "") {
			axiosConfig.headers!.Authorization = `Token ${token}`;
		}

		axiosConfig.baseURL = `http://${baseURL}/`;

		return axiosConfig;
	});

	useEffect(() => {
		if (localStorage.getItem("HIGHLIGHTLY_TOKEN") !== "") {
			axios.get<User>("users/me/").then((response) => {
				setAuthenticated(response.data);
			}).catch(_error => localStorage.setItem("HIGHLIGHTLY_TOKEN", ""));
		}
	}, []);

	return (
		<authContext.Provider value={{ authenticated, setAuthenticated }}>
			<BrowserRouter>
				<Navbar authenticated={authenticated} setAuthenticated={setAuthenticated} />

				<div id="main-content">
					<Toaster toastOptions={{
						style: {
							borderRadius: "10px",
							background: "#333",
							color: "#fff",
						}
					}} />

					<Routes>
						{routes.map((e, index) => {
							return (
								<Route
									key={index}
									path={e.path}
									element={
										!e.authorized || localStorage.getItem("HIGHLIGHTLY_TOKEN")
											? <e.component game={e.name} />
											: <Navigate to="/login" />
									}
								/>
							)
						})}
					</Routes>
				</div>
			</BrowserRouter>
		</authContext.Provider>
	)
}

export default App;