import { render, screen } from "@testing-library/react";
import Gauge from "./Gauge";

test("renders dash when value missing", () => {
  render(<Gauge label="Speed" value={null} unit="kph" />);
  expect(screen.getByText("Speed")).toBeDefined();
  expect(screen.getByText("—")).toBeDefined();
});

test("renders formatted value with unit", () => {
  render(<Gauge label="Battery" value={13.456} unit="V" precision={2} />);
  expect(screen.getByText(/13\.46/)).toBeDefined();
  expect(screen.getByText(/V/)).toBeDefined();
});
