import { createContext } from "react";
import { User } from "../pages/login/interfaces/user";

interface authStore {
	authenticated: User | null;
	setAuthenticated: (user: User) => void;
}

const authContext = createContext<authStore>({} as authStore);

export default authContext;