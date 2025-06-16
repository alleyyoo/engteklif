import { InputTextProps } from "primereact/inputtext";

export interface TextFieldProps extends InputTextProps {
  label: string;
  fullWidth?: boolean;
}
