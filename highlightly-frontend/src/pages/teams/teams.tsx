import React, { useEffect, useState } from 'react';
import { FaSearch } from 'react-icons/fa';
import axios from 'axios';
import { Organization } from './interfaces/team';
import TeamCatalog from './components/team-catalog';
import { useImmer } from 'use-immer';
import './teams.css';

const TeamsPage: React.FunctionComponent<{}> = () => {
	const [searchQuery, setSearchQuery] = useState("");
	const [allTeams, setAllTeams] = useImmer<Organization[]>([]);
	const [teams, setTeams] = useImmer<Organization[]>([]);

	useEffect(() => {
		if (searchQuery) {
			setTeams(allTeams.filter(team => {
				const teamGames = team.teams.map(t => t.game.replaceAll("_", " ").toLowerCase());
				const teamGameIncluded = teamGames.includes(searchQuery.toLowerCase());
				const teamNameIncluded = team.name.toLowerCase().includes(searchQuery.toLowerCase());

				return teamNameIncluded || teamGameIncluded;
			}));
		} else {
			setTeams(allTeams);
		}
	}, [searchQuery]);

	useEffect(() => {
		axios.get<Organization[]>("organizations/").then((response) => {
			setTeams(response.data);
			setAllTeams(response.data);
		}).catch((err) => console.error(err));
	}, []);

	return (
		<div className="container-fluid">
			<div className="row">
				<div className="col-2">
					<div className="input-group mt-4 ms-4">
						<input type="search" id="search-teams" className="form-control" placeholder="Search" value={searchQuery}
							onChange={e => setSearchQuery(e.target.value)} />
						<button type="button" className="btn">
							<FaSearch className="mb-1" />
						</button>
					</div>
				</div>
			</div>

			<TeamCatalog teams={teams} setAllTeams={setAllTeams} setTeams={setTeams} />
		</div>
	)
}

export default TeamsPage;