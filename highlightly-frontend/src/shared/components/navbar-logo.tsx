import React from 'react';
import { FaBars } from 'react-icons/fa';

const NavbarLogo: React.FunctionComponent<{ toggleSidebar: () => void }> = ({ toggleSidebar }) => {
    return (
        <div className="logo-details">
            <div id="logo-name">Highlightly</div>
            <i><FaBars id="sidebar-bars" onClick={toggleSidebar} /></i>
        </div>
    )
}

export default NavbarLogo;