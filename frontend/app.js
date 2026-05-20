const root = document.getElementById("root");

function App() {
  const [message, setMessage] = React.useState("Loading...");

  React.useEffect(() => {
    fetch("/api/")
      .then((response) => response.json())
      .then((data) => setMessage(data.message))
      .catch(() => setMessage("Unable to fetch API"));
  }, []);

  return React.createElement(
    "div",
    { style: { fontFamily: "Arial, sans-serif", margin: "2rem" } },
    React.createElement("h1", null, "mi_calli"),
    React.createElement("p", null, "Minimal React placeholder served by NGINX."),
    React.createElement("p", null, React.createElement("strong", null, message))
  );
}

ReactDOM.render(React.createElement(App), root);
