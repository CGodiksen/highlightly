import React, { ChangeEvent, useState } from 'react';
import ModalBase from '../../../shared/components/modal-base';
import { Organization } from '../interfaces/team';
import { closeBootstrapModal, getErrorMessage, imageToBase64 } from '../../../shared/util';
import { SketchPicker } from 'react-color';
import toast from 'react-hot-toast';
import axios from 'axios';
import { Updater } from 'use-immer';

type UpdateTeamModalFormProps = {
	team: Organization;
	setAllTeams: Updater<Organization[]>;
	setTeams: Updater<Organization[]>;
}

const UpdateTeamModalForm: React.FunctionComponent<UpdateTeamModalFormProps> = ({ team, setAllTeams, setTeams }) => {
	const [name, setName] = useState(team.name);
	const [displayName, setDisplayName] = useState(team.display_name);
	const [alternateNames, setAlternateNames] = useState<string[]>(team.alternate_names !== null ? JSON.parse(team.alternate_names) : []);
	const [logo, setLogo] = useState("");

	const [displayColorPicker, setDisplayColorPicker] = useState(false);
	const [backgroundColor, setBackgroundColor] = useState(team.background_color);

	const [loading, setLoading] = useState(false);

	// Retrieve the uploaded image from the event, convert it to base64, and save it in the state.
	const uploadTeamLogo = (event: ChangeEvent) => {
		const input = event.target as HTMLInputElement

		if (input.files) {
			imageToBase64(URL.createObjectURL(input.files[0])).then((base64) => {
				setLogo(base64);
			})
		}
	}

	const updateTeamInList = (teams: Organization[], newTeam: Organization) => {
		const updatedIndex = teams.findIndex(t => t.id === newTeam.id)!;
		teams[updatedIndex] = newTeam;

		return teams;
	}

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		setLoading(true);

		const data = {
			name: name, logo_base64: logo, background_color: backgroundColor,
			display_name: displayName !== "" ? displayName : null, alternate_names: JSON.stringify(alternateNames.map(name => name.trim()))
		}

		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.put<Organization>(`organizations/${team.id}/`, data).finally(() => setLoading(false)),
			{
				loading: "Updating...",
				success: (response) => {
					setAllTeams((draft) => updateTeamInList(draft, response.data));
					setTeams((draft) => updateTeamInList(draft, response.data));
					closeBootstrapModal(`update-team-${team.id}-modal`);
					setLogo("");

					return "Team updated."
				},
				error: (error) => getErrorMessage(error.response.data)
			}
		);
	}

	const body = (
		<form id={`update-team-${team.id}-form`} className="update-team-form" onSubmit={handleSubmit}>
			<div className="row">
				<div className="col-6">
					<div className="form-group">
						<label className="text-start mb-1" htmlFor="name">Name</label>
						<input type="text" id="name" className="form-control" value={name}
							onChange={e => setName(e.target.value)} required minLength={2} maxLength={128} />
					</div>
				</div>
				<div className="col-6">
					<div className="form-group">
						<label className="text-start mb-1" htmlFor="display-name">Display Name</label>
						<input type="text" id="display-name" className="form-control" value={displayName !== null ? displayName : ""}
							onChange={e => setDisplayName(e.target.value)} minLength={2} maxLength={128} />
					</div>
				</div>
			</div>

			<div className="form-group mt-3">
				<label className="text-start mb-1" htmlFor="alternate-names">Alternate names</label>
				<input type="text" id="alternate-names" className="form-control" value={alternateNames.join(",")}
					onChange={e => setAlternateNames(e.target.value.split(","))} minLength={2} maxLength={128} />
			</div>

			<div className="row mt-3">
				<div className="col-4 d-flex justify-content-center align-items-center">
					<div className="form-group mt-2">
						<label className="btn btn-outline-light">
							Upload new logo
							<input type="file" hidden accept="image/png" onChange={(e) => uploadTeamLogo(e)} />
						</label>
					</div>
				</div>
				<div className="col">
					<div className="form-group">
						<label className="text-start pb-2" htmlFor="url">Background color</label>
						<div className="input-group">
							<button type="button" className="btn pe-5" onClick={() => setDisplayColorPicker(!displayColorPicker)} style={{ "background": backgroundColor }}></button>
							{displayColorPicker &&
								<div style={{ position: 'absolute', zIndex: '999' }}>
									<div style={{ position: 'fixed', top: '0px', right: '0px', bottom: '0px', left: '0px' }} onClick={() => setDisplayColorPicker(false)} />
									<SketchPicker color={backgroundColor} onChangeComplete={(color) => { setBackgroundColor(color.hex) }} />
								</div>
							}
							<input type="text" id="background-color" className="form-control" value={backgroundColor}
								onChange={e => setBackgroundColor(e.target.value)} />
						</div>
					</div>
				</div>
			</div>
		</form>
	);

	const submitButton = <button type="submit" form={`update-team-${team.id}-form`} className="btn btn-primary" disabled={loading}>Update</button>
	return <ModalBase id={`update-team-${team.id}-modal`} title={`Update ${team.name}`} body={body} submitButton={submitButton} />;
}

export default UpdateTeamModalForm;