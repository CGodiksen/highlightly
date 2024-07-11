import React, { useState } from 'react';

type AuthenticationBaseProps = {
	title: string;
	Form: React.FunctionComponent<{ setAlert: (alert: string) => void; }>
}

const AuthenticationBase: React.FunctionComponent<AuthenticationBaseProps> = ({ title, Form }) => {
	const [alert, setAlert] = useState("");

	return (
		<div style={{ background: 'linear-gradient(to right, #377fea, #643eea)' }}>
			<div className="d-flex flex-column min-vh-100 justify-content-center align-items-center">
				<div className="container">
					<div className="row">
						<div className="col-12 col-md-8 offset-md-4 col-lg-4 offset-lg-4">
							<div className="card bg-dark text-white">
								<div className="card-body p-5">
									<h3 className="text-center text-white">{title}</h3>

									{alert && <div className="alert alert-danger p-2 mt-3" role="alert">{alert}</div>}
									<Form setAlert={setAlert} />
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	)
};

export default AuthenticationBase;
