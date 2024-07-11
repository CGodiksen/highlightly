import React, { ReactElement } from 'react';
import { Organization, Team } from '../interfaces/team';
import { BsThreeDots } from 'react-icons/bs';
import axios from 'axios';
import { Updater } from 'use-immer';
import UpdateTeamModalForm from './update-team-modal-form';

type TeamCatalogProps = {
	teams: Organization[];
	setAllTeams: Updater<Organization[]>;
	setTeams: Updater<Organization[]>;
}

const TeamCatalog: React.FunctionComponent<TeamCatalogProps> = ({ teams, setAllTeams, setTeams }) => {
	const deleteTeam = (team: Organization) => {
		if (window.confirm("Are you sure you want to delete the team?")) {
			axios.delete(`organizations/${team.id}/`).then((_response) => {
				setAllTeams((draft) => draft.filter(t => t.id !== team.id));
				setTeams((draft) => draft.filter(t => t.id !== team.id));
			}).catch((err) => console.error(err));
		}
	}

	const refreshTeam = (team: Organization) => {

	}

	const getGameIcon = (team: Team): ReactElement => {
		if (team.game === "COUNTER_STRIKE") {
			return <img className="game-icon mt-1" src={require('../../../assets/cs2-logo.jpg')} alt="Counter-Strike" />
		} else if (team.game === "VALORANT") {
			return <img className="game-icon mt-1" src={require('../../../assets/valorant-logo.png')} alt="Valorant" />
		} else {
			return <img className="game-icon mt-1" src={require('../../../assets/lol-logo.jpg')} alt="League of Legends" />
		}
	}

	return (
		<div className="row pt-4 ps-3 pe-3">
			{teams.map((team, index) => {
				return (
					<div className="col-3" key={index}>
						<div className="card team-card" style={{ "background": team.background_color }}>
							<div className="row">
								<div className="col">
									{team.teams.map((organization_team) => {
										return <a className="ms-2 icon" target="_blank" rel="noopener noreferrer"
											href={organization_team.url}>{getGameIcon(organization_team)}</a>
									})}
								</div>
								<div className="col">
									<i className="icon float-end team-dropdown" data-bs-toggle="dropdown" aria-expanded="false">
										<BsThreeDots fontSize="40" className="me-3 mt-1" />
									</i>
									<ul className="dropdown-menu text-small shadow dropdown-menu-end">
										<li><a className="dropdown-item" data-bs-toggle="modal" data-bs-target={`#update-team-${team.id}-modal`}>Update</a></li>
										<li><a className="dropdown-item dropdown-delete-item" onClick={() => deleteTeam(team)}>Delete</a></li>
										<div className="dropdown-divider"></div>
										<li><a className="dropdown-item" onClick={() => refreshTeam(team)}>Refresh</a></li>
									</ul>
								</div>
							</div>
							<div className="row">
								<div className="col d-flex justify-content-center">
									<img className="mb-2 team-icon" src={`data:image/png;base64,${team.logo}`} />
								</div>
							</div>
							<div className="row">
								<div className="col d-flex justify-content-center mb-2 pt-3 pb-3">
									<div className="h4">{team.name} {team.display_name !== null && `(${team.display_name})`}</div>
								</div>
							</div>
						</div>

						<UpdateTeamModalForm team={team} setAllTeams={setAllTeams} setTeams={setTeams} key={team.id} />
					</div>
				);
			})}
		</div>
	)
}

export default TeamCatalog;