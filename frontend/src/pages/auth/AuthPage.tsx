import { Form, message } from "antd";
import { AuthPageStyle } from "./AuthPage.style";
import { AuthPageLoginTypes } from "./AuthPage.types";
import { TextField } from "../../components/TextField/TextField";
import { Message } from "primereact/message";
import { Button } from "primereact/button";

export const AuthPage = () => {
  const classes = AuthPageStyle();
  const [form] = Form.useForm();

  const loginHandler = async (form: AuthPageLoginTypes) => {
    console.log("Login form submitted:", form);
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
            <Form.Item
              name="username"
              rules={[
                {
                  required: true,
                  message: "Lütfen kullanıcı adını giriniz.",
                },
              ]}
            >
              <TextField
                label="Kullanıcı Adı"
                placeholder="Kullanıcı adınızı giriniz"
                fullWidth
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[
                {
                  required: true,
                  message: "Lütfen şifrenizi giriniz.",
                },
              ]}
            >
              <TextField
                type="password"
                label="Şifre"
                placeholder="Şifrenizi giriniz"
                fullWidth
              />
            </Form.Item>
            <div className={classes.formFooter}>
              <a href="/">Şifremi Unuttum</a>
              <Form.Item>
                <Button label="Giriş Yap" className="full-width" />
              </Form.Item>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
};
