import React, { useState } from 'react';
import { User } from '../../pages/login/interfaces/user';
import NavbarItems from './navbar-items';
import NavbarLogo from './navbar-logo';
import NavbarUser from './navbar-user';
import './navbar.css';

type NavbarProps = {
	authenticated: User | null; 
	setAuthenticated: (user: User | null) => void;
}

const Navbar: React.FunctionComponent<NavbarProps> = ({ authenticated, setAuthenticated }) => {
	const [showSidebar, setShowSidebar] = useState(!!localStorage.getItem('HIGHLIGHTLY_SHOW_SIDEBAR'));

	const toggleSidebar = () => {
		localStorage.setItem('HIGHLIGHTLY_SHOW_SIDEBAR', !showSidebar ? 'true' : '');
		setShowSidebar(!showSidebar);
	}

	return (
		<div className={showSidebar ? "sidebar open" : "sidebar"}>
			<NavbarLogo toggleSidebar={toggleSidebar} />
			<ul className="nav-list">
				<NavbarItems authenticated={authenticated} />

				{/* Only show the user section of the navbar if the user is logged in.*/}
				{authenticated && <NavbarUser authenticated={authenticated} setAuthenticated={setAuthenticated} />}
			</ul>
		</div>
	)
};

export default Navbar;