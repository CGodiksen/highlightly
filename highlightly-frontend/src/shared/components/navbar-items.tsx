import React from 'react';
import { Link } from 'react-router-dom';
import { User } from '../../pages/login/interfaces/user';
import routes from '../data/routes';

const NavbarItems: React.FunctionComponent<{ authenticated: User | null }> = ({ authenticated }) => {
    return (
        <>
            {routes.map((route, index) => {
                if (route.icon !== undefined && (route.authorized === (authenticated !== null))) {
                    return (
                        <li key={index} className="nav-text">
							<Link to={route.path}>
								<i>{route.icon}</i>
								<span className="item-name ms-2">{route.name}</span>
							</Link>
                            <span className="tooltip">{route.name}</span>
                        </li>
                    );
                }
            })}
        </>
    )
}

export default NavbarItems;
