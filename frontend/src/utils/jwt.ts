import { jwtDecode } from "jwt-decode";

export interface TokenType {
  token_type: string;
  exp: number;
  iat: number;
  jti: string;
  user_id: number;
  is_admin: boolean;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
}

export const verifyToken = (token: string) => {
  if (!token) return false;
  const tokenDecode: TokenType = jwtDecode(token || "");
  console.log(tokenDecode);
  if (tokenDecode.exp! * 1000 < Date.now()) {
    return false;
  }
  return true;
};
