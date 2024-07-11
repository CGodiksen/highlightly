import { ReactElement } from "react";

export default interface Route {
	path: string;
	name: string;
	component: any;
	exact: boolean;
	authorized?: boolean;
	icon?: ReactElement;
}