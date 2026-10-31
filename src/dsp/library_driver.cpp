// SPDX-License-Identifier: MIT. Local direct Ingen clock; no audio device driver.
#include <ingen/World.hpp>
#include <ingen/EngineBase.hpp>
#include <chrono>
#include <csignal>
#include <thread>
static volatile std::sig_atomic_t stopped=0;
static void stop(int){stopped=1;}
int main(int argc,char** argv){
  std::signal(SIGTERM,stop);std::signal(SIGINT,stop);
  ingen::World world(nullptr,nullptr,nullptr);world.load_configuration(argc,argv);
  if(!world.load_module("server")||!world.engine())return 2;
  auto engine=world.engine();engine->init(48000.,128,4096);
  if(!engine->activate())return 3;engine->listen();
  auto next=std::chrono::steady_clock::now();
  const auto period=std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(128./48000.));
  while(!stopped){
    engine->advance(128);engine->run(128);if(!engine->main_iteration())break;
    next+=period;std::this_thread::sleep_until(next);
    if(std::chrono::steady_clock::now()-next>std::chrono::seconds(1))next=std::chrono::steady_clock::now();
  }
  engine->deactivate();return 0;
}
