import { Card, Form, message } from "antd";
import { AuthPageStyle } from "./AuthPage.style";

export const AuthPage = () => {
  const classes = AuthPageStyle();
  const [form] = Form.useForm();

  const loginHandler = async (form: AuthPageLoginTypes) => {
  };

  return (
    <div className={classes.authContainer}>
      <img src="/login.png" className={classes.authImage} alt="" />
      <div className={classes.authDiv}>
        <img src="/logo.svg" className={classes.authLogo} alt="" />
        <p className={classes.authTitle}>Panel Giriş Yap</p>
        <div className={classes.inputContainer}>
          <Form
            name="login"
            initialValues={{
              email: "",
              password: "",
            }}
            form={form}
            onFinish={loginHandler}
          >
            
          </Form>
        </div>
      </div>
    </div>
  );
};
