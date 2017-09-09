FROM jupyter/minimal-notebook

RUN pip install flit
RUN conda install -y openjdk
RUN mkdir $HOME/bin
ENV PATH $HOME/bin:$PATH
WORKDIR $HOME/bin
RUN wget https://raw.githubusercontent.com/technomancy/leiningen/stable/bin/lein
RUN chmod +x lein

WORKDIR /clojure-kernel
COPY . .
RUN flit install --symlink
RUN clojure-kernel install --user

CMD start.sh jupyter lab
