import React from 'react';

type ModalBaseProps = {
	id: string;
	title: string;
	body: React.ReactElement;
	submitButton: JSX.Element;
	size?: string;
}

const ModalBase: React.FunctionComponent<ModalBaseProps> = ({ id, title, body, submitButton, size }) => {
	return (
		<div className="modal fade" tabIndex={-1} id={id} aria-hidden="true">
			<div className={"modal-dialog " + (size ? size : "")}>
				<div className="modal-content">
					<div className="modal-header">
						<h5 className="modal-title">{title}</h5>
						<button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
					</div>
					<div className="modal-body">
						{body}
					</div>
					<div className="modal-footer">
						<button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
						{submitButton}
					</div>
				</div>
			</div>
		</div>
	)
}

export default ModalBase;