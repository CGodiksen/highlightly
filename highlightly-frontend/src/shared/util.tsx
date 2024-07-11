import { ReactElement } from "react";

// Extract all values from the given object containing data.
const getValues = (data: any): string[] => {
	if (typeof data !== "object") {
		return data;
	}

	return Object.values(data).flatMap(v => ` ${getValues(v)}`);
}

// Extract all values from the given object containing data and return it as a list group.
export const getErrorMessage = (data: Object): ReactElement => {
	const values = getValues(data);

	return (
		<ul className="mb-0 list-unstyled">
			{values.map((value, index) => <li key={index}>{value.trim().charAt(0).toUpperCase() + value.trim().slice(1)}</li>)}
		</ul>
	);
}

export const imageToBase64 = async (imageUrl: string): Promise<string> => {
	const blob = await fetch(imageUrl).then(r => r.blob());
	
	return new Promise((resolve, _) => {
		const reader = new FileReader();
		reader.onloadend = () => resolve(reader.result as string);
		reader.readAsDataURL(blob);
	});
};

// Close the Bootstrap modal manually.
export const closeBootstrapModal = (modalId: string): void => {
	var closeModalBtn = document.createElement("button")!;
	closeModalBtn.setAttribute("data-bs-dismiss", "modal")
	document.getElementById(modalId)?.appendChild(closeModalBtn)
	closeModalBtn.click()
	closeModalBtn.remove()

	document.getElementsByClassName("modal-backdrop fade show")[0].remove()
}
