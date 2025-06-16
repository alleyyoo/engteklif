import { FloatLabel } from "primereact/floatlabel";
import { TextFieldProps } from "./TextField.props";
import { InputText } from "primereact/inputtext";

export const TextField = (props: TextFieldProps) => {
  const { id, label, fullWidth = true, required, ...rest } = props;
  return (
    <FloatLabel>
      <InputText id={id} {...rest} className={fullWidth ? "full-width" : ""} />
      <label htmlFor={id}>
        {label} {required && <span className="text-danger">*</span>}
      </label>
    </FloatLabel>
  );
};
