import { JSX } from "react";
import { Navbar } from "../Navbar/Navbar";
import { Content } from "antd/es/layout/layout";

export const DefaultLayout = ({ children }: { children: JSX.Element }) => {
  return <div>
    <Navbar />
    <Content>
    {children}
    </Content>
  </div>;
};
