mod cli;
mod config;
mod context;
mod correction;
mod interaction;
mod persona;

fn main() {
    let mut arguments: Vec<String> = std::env::args().skip(1).collect();
    let shell_transport = arguments
        .first()
        .is_some_and(|arg| arg == "--shell-transport");
    if shell_transport {
        arguments.remove(0);
        if !matches!(
            arguments.first().map(String::as_str),
            Some("session" | "event")
        ) {
            eprintln!("zako: shell transport only supports session/event");
            std::process::exit(1);
        }
    }
    if let Err(error) = cli::run(arguments) {
        eprintln!("zako: {error}");
        std::process::exit(1);
    }
    if shell_transport {
        println!("S:0");
    }
}
