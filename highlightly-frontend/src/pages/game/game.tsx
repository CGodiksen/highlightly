import React from 'react';
import UpcomingVideos from './components/upcoming-videos';
import UpcomingExtraVideos from './components/upcoming-extra-videos';
import UpcomingShortVideos from './components/upcoming-short-videos';
import './game.css';

const GamePage: React.FunctionComponent<{ game: string }> = ({ game }) => {
	return (
		<div id="game-container" className="container-fluid" key={game}>
			<div className="row h-100">
				<div className="col-7 ps-3 pe-1">
					<UpcomingVideos game={game} />
				</div>

				<div className="col h-100 ps-1">
					<div className="row h-50">
						<div className="col pb-2">
							<UpcomingExtraVideos />
						</div>
					</div>
					<div className="row h-50">
						<div className="col pt-2">
							<UpcomingShortVideos />
						</div>
					</div>
				</div>
			</div>
		</div>
	)
}

export default GamePage;