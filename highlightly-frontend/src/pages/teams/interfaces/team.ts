export interface Team {
	id: number;
	game: "VALORANT" | "COUNTER_STRIKE" | "LEAGUE_OF_LEGENDS";
	nationality: string;
	ranking: number;
	url: string;
}

export interface Organization {
	id: number;
	name: string;
	logo: string;
	background_color: string;
	display_name: string | null;
	alternate_names: string | null;
	teams: Team[];
}
