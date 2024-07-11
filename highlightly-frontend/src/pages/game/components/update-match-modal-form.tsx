import React, { useState } from 'react';
import ModalBase from '../../../shared/components/modal-base';
import { UpcomingMatch, VideoMetadata } from '../interfaces/match';
import axios from 'axios';
import toast from 'react-hot-toast';
import { closeBootstrapModal, getErrorMessage } from '../../../shared/util';
import { Updater } from 'use-immer';

const UpdateMatchModalForm: React.FunctionComponent<{ match: UpcomingMatch, setUpcomingMatches: Updater<UpcomingMatch[]> }> = ({ match, setUpcomingMatches }) => {
	const [title, setTitle] = useState(match.video_metadata.title);
	const [description, setDescription] = useState(match.video_metadata.description);
	const [tags, setTags] = useState(match.video_metadata.tags);
	const [language, setLanguage] = useState(match.video_metadata.language);
	const [categoryId, setCategoryId] = useState(match.video_metadata.category_id);
	const [loading, setLoading] = useState(false);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		setLoading(true);

		const data = { title: title, description: description, tags: tags, language: language, category_id: categoryId }

		// Provide handlers for when the request is successful and for validation errors.
		toast.promise(axios.put<VideoMetadata>(`video_metadata/${match.video_metadata.id}/`, data).finally(() => setLoading(false)),
			{
				loading: "Updating...",
				success: (response) => {
					setUpcomingMatches((draft) => {
						const updatedIndex = draft.findIndex(m => m.id === match.id);
						draft[updatedIndex].video_metadata = response.data;
					});
					
					closeBootstrapModal(`update-match-${match.id}-modal`);

					return "Match updated.";
				},
				error: (error) => getErrorMessage(error.response.data)
			}
		);
	}

	const body = (
		<form id={`update-match-${match.id}-form`} onSubmit={handleSubmit}>
			<div className="form-group">
				<label className="text-start mb-1" htmlFor="title">Title</label>
				<input type="text" id="title" className="form-control" value={title}
					onChange={e => setTitle(e.target.value)} required minLength={2} maxLength={128} />
			</div>

			<div className="form-group mt-3">
				<label className="form-label mb-1" htmlFor="description">Description</label>
				<textarea id="description" className="form-control" value={description} onChange={e => setDescription(e.target.value)} />
			</div>

			<div className="form-group mt-3">
				<label className="form-label mb-1" htmlFor="tags">Tags</label>
				<textarea id="tags" className="form-control" value={tags} onChange={e => setTags(e.target.value)} />
			</div>

			<div className="row mt-3">
				<div className="col-8">
					<div className="form-group">
						<label className="text-start mb-1" htmlFor="language">Language</label>
						<input type="text" id="language" className="form-control" value={language}
							onChange={e => setLanguage(e.target.value)} required minLength={2} maxLength={128} />
					</div>
				</div>
				<div className="col">
					<div className="form-group">
						<label className="form-label mb-1" htmlFor="categoryId">Category ID</label>
						<input type="number" id="categoryId" className="form-control number-input" min={1} max={99} step={1} value={categoryId}
							onChange={e => setCategoryId(parseInt(e.target.value))} />
					</div>
				</div>
			</div>
		</form>
	);

	const submitButton = <button type="submit" form={`update-match-${match.id}-form`} className="btn btn-primary" disabled={loading}>Update</button>
	return <ModalBase id={`update-match-${match.id}-modal`} title={`Update match`} body={body} submitButton={submitButton} />;
}

export default UpdateMatchModalForm;