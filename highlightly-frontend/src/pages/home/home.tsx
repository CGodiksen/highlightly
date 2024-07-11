import React from 'react';
import LinkCard from './components/link-card';
import UpcomingVideos from './components/upcoming-videos';
import './home.css';

const HomePage: React.FunctionComponent<{}> = () => {
	return (
		<div id="home-container" className="container-fluid">
			<div className="row pt-5 pb-5 d-flex justify-content-center">
				<div className="col-3 me-5">
					<LinkCard game={"Counter-Strike"} />
				</div>
				<div className="col-3 me-2 ms-2">
					<LinkCard game={"Valorant"} />
				</div>
				<div className="col-3 ms-5">
					<LinkCard game={"League of Legends"} />
				</div>
			</div>

			<div id="home-page-info" className="row d-flex justify-content-center">
				<div className="col-8 h-100">
					<UpcomingVideos />
				</div>
			</div>
		</div>
	)
}

export default HomePage;