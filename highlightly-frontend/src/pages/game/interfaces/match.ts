import { Team } from "../../teams/interfaces/team";

interface Tournament {
	id: number;
	game: "VALORANT" | "COUNTER_STRIKE" | "LEAGUE_OF_LEGENDS";
	name: string;
	logo: string;
	url: string;
}

export interface VideoMetadata {
	id: number;
	match: number;
	title: string;
	description: string;
	tags: string;
	thumbnail: string;
	thumbnail_match_frame_time: number;
	language: string;
	category_id: number;
}

export interface UpcomingMatch {
	id: number;
	team_1: Team;
	team_2: Team;
	tournament: Tournament;
	tournament_context: string;
	format: "BEST_OF_1" | "BEST_OF_3" | "BEST_OF_5"
	tier: number;
	url: string;
	created_at: string;
	start_datetime: string;
	estimated_end_datetime: string;
	create_video: boolean;
	finished: boolean;
	highlighted: boolean;
	video_metadata: VideoMetadata;
}
