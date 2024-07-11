import { FaHome } from "react-icons/fa";
import { RiTeamFill } from "react-icons/ri";
import { MdLogin } from "react-icons/md";
import LoginPage from "../../pages/login/login";
import HomePage from "../../pages/home/home";
import NotFoundPage from "../../pages/not-found";
import Route from "../interfaces/route";
import GamePage from "../../pages/game/game";
import TeamsPage from "../../pages/teams/teams";

const routes: Route[] = [
	{
		path: "/",
		name: "Home",
		component: HomePage,
		exact: true,
		icon: <FaHome className="icon" />,
		authorized: true,
	},
	{
		path: "/counter-strike",
		name: "Counter-Strike",
		component: GamePage,
		exact: true,
		icon: <img className="game-icon" src={require('../../assets/cs2-logo.jpg')} alt="Counter-Strike" />,
		authorized: true,
	},
	{
		path: "/valorant",
		name: "Valorant",
		component: GamePage,
		exact: true,
		icon: <img className="game-icon" src={require('../../assets/valorant-logo.png')} alt="Valorant" />,
		authorized: true,
	},
	{
		path: "/league-of-legends",
		name: "League of Legends",
		component: GamePage,
		exact: true,
		icon: <img className="game-icon" src={require('../../assets/lol-logo.jpg')} alt="League of Legends" />,
		authorized: true,
	},
	{
		path: "/teams",
		name: "Teams",
		component: TeamsPage,
		exact: true,
		icon: <RiTeamFill className="icon" />,
		authorized: true,
	},
	{
		path: "/login",
		name: "Login",
		component: LoginPage,
		exact: true,
		icon: <MdLogin />,
		authorized: false,
	},
	{
		path: "*",
		name: "Not found",
		component: NotFoundPage,
		exact: true,
	}
];

export default routes;