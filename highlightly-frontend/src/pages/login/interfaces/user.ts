export interface LoginResponse {
	token: string;
}

export interface User {
	id: number;
	email: string;
	is_staff: boolean;
	is_active: boolean;
	is_admin: boolean;
	last_login: string;
	date_joined: string;
}
