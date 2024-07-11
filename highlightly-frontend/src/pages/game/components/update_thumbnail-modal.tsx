import React from 'react';
import { UpcomingMatch } from '../interfaces/match';
import { IoMdRefresh } from 'react-icons/io';
import toast from 'react-hot-toast';
import axios from 'axios';
import { Updater } from 'use-immer';
import { getErrorMessage } from '../../../shared/util';

const UpdateThumbnailModal: React.FunctionComponent<{ match: UpcomingMatch, setUpcomingMatches: Updater<UpcomingMatch[]> }> = ({ match, setUpcomingMatches }) => {
	const refreshMatchFrame = (matchFrameTimeChange: number | null) => {
		const data = matchFrameTimeChange ? {"match_frame_time": match.video_metadata.thumbnail_match_frame_time + matchFrameTimeChange} : {}

		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.post<UpcomingMatch>(`matches/${match.id}/refresh_match_frame/`, data),
			{
				loading: "Refreshing...",
				success: (response) => {
					setUpcomingMatches((draft) => {
						const updatedIndex = draft.findIndex(m => m.id === match.id);
						draft[updatedIndex] = response.data;
					});

					return "Refreshed thumbnail.";
				},
				error: (error) => getErrorMessage(error.response.data),
			}
		);
	}
	
	return (
		<div className="modal fade" tabIndex={-1} id={`update-match-${match.id}-thumbnail-modal`} aria-hidden="true">
			<div className={"modal-dialog modal-xl"}>
				<div className="modal-content">
					<div className="modal-header">
						<h5 className="modal-title">Update thumbnail</h5>
						<button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
					</div>
					<div className="modal-body d-flex justify-content-center align-items-center">
						<div>
							<img className="thumbnail rounded" src={`data:image/png;base64,${match.video_metadata.thumbnail}`} />

							<div className="btn-group thumbnail-toolbar" role="group">
								<button type="button" className="btn btn-danger" onClick={() => refreshMatchFrame(-1)}>-1</button>
								<button type="button" className="btn btn-danger" onClick={() => refreshMatchFrame(-0.1)}>-0.1</button>
								<button type="button" className="btn btn-primary d-flex align-items-center" onClick={() => refreshMatchFrame(null)}><IoMdRefresh /></button>
								<button type="button" className="btn btn-success" onClick={() => refreshMatchFrame(0.1)}>+0.1</button>
								<button type="button" className="btn btn-success" onClick={() => refreshMatchFrame(1)}>+1</button>
							</div>
						</div>
					</div>
					<div className="modal-footer">
						<button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
					</div>
				</div>
			</div>
		</div>
	)
}

export default UpdateThumbnailModal;