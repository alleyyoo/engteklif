export const px2rem = (px: number): string => {
  const baseFontSize = 16;
  const remValue = px / baseFontSize;
  return `${remValue}rem`;
};
