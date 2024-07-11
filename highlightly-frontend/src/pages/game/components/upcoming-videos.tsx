import React, { useEffect, useState } from 'react';
import { getErrorMessage } from '../../../shared/util';
import { BsThreeDots } from 'react-icons/bs';
import { UpcomingMatch } from '../interfaces/match';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useImmer } from 'use-immer';
import UpdateMatchModalForm from './update-match-modal-form';
import UpdateThumbnailModal from './update_thumbnail-modal';

const UpcomingVideos: React.FunctionComponent<{ game: string }> = ({ game }) => {
	const [loading, setLoading] = useState(false);
	const [upcomingMatches, setUpcomingMatches] = useImmer<UpcomingMatch[]>([]);
	const queryParams = `?game=${game.toUpperCase().replaceAll("-", "_").replaceAll(" ", "_")}`;

	useEffect(() => {
		setLoading(true);
		
		axios.get<UpcomingMatch[]>(`matches/${queryParams}`).then((response) => {
			setLoading(false);
			setUpcomingMatches(response.data);
		}).catch((err) => console.error(err));
	}, [])

	const scrapeMatches = () => {
		const data = { game: game.toLowerCase().replaceAll(" ", "-") };

		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.post<UpcomingMatch[]>("matches/scrape_matches/", data),
			{
				loading: "Scraping...",
				success: (response) => {
					setUpcomingMatches(response.data);
					return "Scraped upcoming matches.";
				},
				error: (error) => getErrorMessage(error.response.data),
			}
		);
	}

	const scrapeFinishedMatch = (match: UpcomingMatch) => {
		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.post<UpcomingMatch>(`matches/${match.id}/scrape_finished_match/`),
			{
				loading: "Scraping...",
				success: "Scraped match.",
				error: (error) => getErrorMessage(error.response.data),
			}
		);
	}

	const checkMatchStatus = (match: UpcomingMatch) => {
		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.post<UpcomingMatch>(`matches/${match.id}/check_match_status/`),
			{
				loading: "Checking...",
				success: "Checking...",
				error: (error) => getErrorMessage(error.response.data),
			}
		);
	}

	const deleteAllMatches = () => {
		if (window.confirm("Are you sure you want to delete all matches?")) {
			upcomingMatches.forEach(match => {
				axios.delete(`matches/${match.id}/${queryParams}`).then((_response) => {
					setUpcomingMatches((draft) => draft.filter(m => m.id !== match.id));
				}).catch((err) => console.error(err));
			})
		}
	}

	const deleteMatch = (match: UpcomingMatch) => {
		if (window.confirm("Are you sure you want to delete the match?")) {
			axios.delete(`matches/${match.id}/${queryParams}`).then((_response) => {
				setUpcomingMatches((draft) => draft.filter(m => m.id !== match.id));
			}).catch((err) => console.error(err));
		}
	}

	return (
		<div id="upcoming-videos" className="card shadow-card m-1 game-detail-card h-100">
			<div className="row pb-1">
				<div className="col">
					<h5 className="card-title">Upcoming videos</h5>
				</div>

				<div className="col">
					<i id="upcoming-videos-dropdown" className="icon float-end" data-bs-toggle="dropdown" aria-expanded="false">
						<BsThreeDots fontSize="40" className="me-3" />
					</i>
					<ul className="dropdown-menu text-small shadow dropdown-menu-end">
						<li><a className="dropdown-item" onClick={() => scrapeMatches()}>Scrape upcoming matches</a></li>
						<li><a className="dropdown-item" onClick={() => deleteAllMatches()}>Delete all matches</a></li>
					</ul>
				</div>
			</div>

			{upcomingMatches.map((match, index) => {
				return (
					<div className="row pt-2 pb-2 ps-3" key={index}>
						<div className="col-3 d-flex align-items-center justify-content-center">
							<img className="thumbnail rounded" src={`data:image/png;base64,${match.video_metadata.thumbnail}`} />
						</div>

						<div className="col-8 ps-1">
							<div className="row pt-1">
								<div className="col text-truncate">
									{match.video_metadata.title}
								</div>
							</div>
							<div className="row">
								<div className="col">
									<p className="description">{match.video_metadata.description}</p>
								</div>
							</div>
						</div>

						<div className="col">
							<i className="icon float-end upcoming-video-dropdown d-flex justify-content-center align-items-start" data-bs-toggle="dropdown" aria-expanded="false">
								<BsThreeDots fontSize="25" className="me-3" />
							</i>
							<ul className="dropdown-menu text-small shadow dropdown-menu-end">
								<li><a className="dropdown-item" data-bs-toggle="modal" data-bs-target={`#update-match-${match.id}-modal`}>Update</a></li>
								<li><a className="dropdown-item dropdown-delete-item" onClick={() => deleteMatch(match)}>Delete</a></li>
								<div className="dropdown-divider"></div>
								<li><a className="dropdown-item" data-bs-toggle="modal" data-bs-target={`#update-match-${match.id}-thumbnail-modal`}>Update thumbnail</a></li>
								<div className="dropdown-divider"></div>
								<li><a className="dropdown-item" onClick={() => scrapeFinishedMatch(match)}>Scrape finished match</a></li>
								<li><a className="dropdown-item" onClick={() => checkMatchStatus(match)}>Check match status</a></li>
							</ul>
						</div>

						<UpdateMatchModalForm match={match} setUpcomingMatches={setUpcomingMatches} />
						<UpdateThumbnailModal match={match} setUpcomingMatches={setUpcomingMatches} />
					</div>
				);
			})}

			{loading &&
				<div className="spinner-border align-self-center mt-auto mb-auto" role="status">
					<span className="visually-hidden">Retrieving upcoming videos...</span>
				</div>
			}
		</div>
	)
}

export default UpcomingVideos;