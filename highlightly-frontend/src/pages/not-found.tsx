import React from 'react';
import { BiErrorAlt } from 'react-icons/bi';

const NotFoundPage: React.FunctionComponent<{}> = () => {
	return (
		<div className="container-fluid pt-4 pb-4 d-flex align-items-center justify-content-center" style={{ height: '100vh' }}>
			<div className="card h-25 w-25 ms-4 me-4 d-flex align-items-center justify-content-center">
				<BiErrorAlt className="icon" fontSize="60px" />
				<h4 className="pb-2">Page not found.</h4>
				<p>Sorry, we can't find the page you are looking for.</p>
			</div>
		</div>
	)
}

export default NotFoundPage;