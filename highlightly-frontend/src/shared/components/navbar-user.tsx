import React from 'react';
import { useNavigate } from 'react-router-dom';
import { User } from '../../pages/login/interfaces/user';
import axios from 'axios';

type NavbarUserProps = {
	authenticated: User | null;
	setAuthenticated: (user: User | null) => void;
}

const NavbarUser: React.FunctionComponent<NavbarUserProps> = ({ authenticated, setAuthenticated }) => {
	const navigate = useNavigate();

	const handleSignOut = (e: React.MouseEvent) => {
		e.preventDefault();
		
		axios.post<User>("users/logout/").then((_response) => {
			setAuthenticated(null);
			localStorage.setItem("HIGHLIGHTLY_TOKEN", "");
	
			navigate("/login");
		}).catch(error => console.error(error));
	}

	return (
		<li className="user">
			<div className="dropup">
				<a href="#" className="d-flex align-items-center text-white text-decoration-none dropdown-toggle"
					id="dropdownUser" data-bs-toggle="dropdown" aria-expanded="false">
					<img className="m-2 me-3 profile-picture" src={ require('../../assets/default.png') } />
					<strong id="username" className="text-truncate">{authenticated?.email}</strong>
				</a>
				<ul className="dropdown-menu dropdown-menu-dark text-small shadow"
					aria-labelledby="dropdownUser">
					<li><button className="dropdown-item" onClick={handleSignOut}>Sign out</button></li>
				</ul>
			</div>
		</li>
	)
}

export default NavbarUser;
