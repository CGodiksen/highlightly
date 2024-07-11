import React from 'react';

const LinkCard: React.FunctionComponent<{ game: string }> = ({ game }) => {
	return (
		<div className="link-card card shadow-card m-1">
			<h5 className="card-title">{game}</h5>
		</div>
	)
}

export default LinkCard;